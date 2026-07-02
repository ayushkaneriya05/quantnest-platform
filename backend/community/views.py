from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Bookmark, Comment, CommunityProfile, Follow, ModerationAction, Post, PostReport, Reaction, StrategyRoom, Topic
from .serializers import (
    BookmarkSerializer,
    CommentSerializer,
    CommunityProfileSerializer,
    FollowSerializer,
    ModerationActionSerializer,
    PostReportSerializer,
    PostSerializer,
    ReactionSerializer,
    StrategyRoomSerializer,
    TopicSerializer,
)
from .services import CommunityService


class CommunityProfileViewSet(viewsets.ModelViewSet):
    serializer_class = CommunityProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "user__username"
    lookup_url_kwarg = "username"

    def get_queryset(self):
        return CommunityProfile.objects.select_related("user").filter(Q(is_discoverable=True) | Q(user=self.request.user))

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        profile, _ = CommunityProfile.objects.get_or_create(user=request.user)
        if request.method == "PATCH":
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(self.get_serializer(profile).data)


class TopicViewSet(viewsets.ModelViewSet):
    serializer_class = TopicSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "slug"

    def get_queryset(self):
        return Topic.objects.all()


class StrategyRoomViewSet(viewsets.ModelViewSet):
    serializer_class = StrategyRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StrategyRoom.objects.filter(is_active=True).select_related("strategy", "listing", "owner")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["get"])
    def posts(self, request, pk=None):
        room = self.get_object()
        posts = room.posts.filter(status="PUBLISHED").annotate(
            reactions_count=Count("reactions", distinct=True),
            comments_count=Count("comments", distinct=True),
        )
        return Response(PostSerializer(posts, many=True, context={"request": request}).data)


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Post.objects.filter(status__in=["PUBLISHED", "LOCKED"]).select_related("author", "topic", "strategy_room", "strategy_room__strategy").prefetch_related("attachments")
        topic = self.request.query_params.get("topic")
        post_type = self.request.query_params.get("type")
        strategy_room = self.request.query_params.get("strategy_room")
        search = self.request.query_params.get("search")
        if topic:
            qs = qs.filter(topic__slug=topic)
        if post_type:
            qs = qs.filter(post_type=post_type)
        if strategy_room:
            qs = qs.filter(strategy_room_id=strategy_room)
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(body__icontains=search) | Q(hashtags__contains=[search]))
        return qs.annotate(reactions_count=Count("reactions", distinct=True), comments_count=Count("comments", distinct=True))

    def perform_create(self, serializer):
        post = serializer.save(author=self.request.user)
        if post.topic:
            post.topic.posts_count = post.topic.posts.count()
            post.topic.save(update_fields=["posts_count", "updated_at"])
        if post.status == "PUBLISHED":
            CommunityService.publish_post(post)

    @action(detail=True, methods=["post"])
    def react(self, request, pk=None):
        post = self.get_object()
        reaction_type = request.data.get("reaction_type", "LIKE")
        reaction, created = Reaction.objects.get_or_create(user=request.user, post=post, reaction_type=reaction_type)
        if not created:
            reaction.delete()
            return Response({"active": False})
        return Response({"active": True, "reaction": ReactionSerializer(reaction).data})

    @action(detail=True, methods=["post"])
    def bookmark(self, request, pk=None):
        post = self.get_object()
        bookmark, created = Bookmark.objects.get_or_create(user=request.user, post=post)
        if not created:
            bookmark.delete()
            return Response({"active": False})
        return Response({"active": True})


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Comment.objects.filter(is_hidden=False).select_related("author", "post")
        post_id = self.request.query_params.get("post")
        if post_id:
            qs = qs.filter(post_id=post_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class BookmarkViewSet(viewsets.ModelViewSet):
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Bookmark.objects.filter(user=self.request.user).select_related("post", "post__author", "post__topic")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FollowViewSet(viewsets.ModelViewSet):
    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Follow.objects.filter(follower=self.request.user).select_related("following")

    def create(self, request, *args, **kwargs):
        following_id = request.data.get("following")
        if str(following_id) == str(request.user.id):
            return Response({"detail": "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)
        user = get_user_model().objects.get(id=following_id)
        follow, _ = Follow.objects.get_or_create(follower=request.user, following=user)
        return Response(self.get_serializer(follow).data, status=status.HTTP_201_CREATED)


class PostReportViewSet(viewsets.ModelViewSet):
    serializer_class = PostReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return PostReport.objects.all().select_related("reporter", "post", "comment")
        return PostReport.objects.filter(reporter=self.request.user).select_related("post", "comment")

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class ModerationActionViewSet(viewsets.ModelViewSet):
    serializer_class = ModerationActionSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return ModerationAction.objects.all().select_related("moderator", "post", "comment")

    def perform_create(self, serializer):
        action = serializer.save(moderator=self.request.user)
        if action.post and action.action == "HIDE":
            action.post.status = "HIDDEN"
            action.post.save(update_fields=["status", "updated_at"])
        if action.post and action.action == "LOCK":
            action.post.status = "LOCKED"
            action.post.save(update_fields=["status", "updated_at"])


class StrategyRoomByStrategyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, strategy_id):
        room = StrategyRoom.objects.filter(strategy_id=strategy_id, is_active=True).select_related("strategy", "owner", "listing").first()
        if not room:
            return Response({"detail": "Strategy room not found."}, status=404)
        return Response(StrategyRoomSerializer(room).data)
