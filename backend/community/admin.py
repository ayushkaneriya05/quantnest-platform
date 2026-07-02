from django.contrib import admin

from .models import Bookmark, Comment, CommunityProfile, Follow, ModerationAction, Post, PostAttachment, PostReport, Reaction, StrategyRoom, Topic


admin.site.register(CommunityProfile)
admin.site.register(Topic)
admin.site.register(StrategyRoom)
admin.site.register(Post)
admin.site.register(PostAttachment)
admin.site.register(Comment)
admin.site.register(Reaction)
admin.site.register(Bookmark)
admin.site.register(Follow)
admin.site.register(PostReport)
admin.site.register(ModerationAction)
