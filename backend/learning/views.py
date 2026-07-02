from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Assignment, AssignmentSubmission, Certificate, Course, CourseEnrollment, LearningPath, LearningRecommendation, Lesson, LessonProgress, Quiz, QuizAttempt, UserLearningSignal
from .serializers import AssignmentSerializer, AssignmentSubmissionSerializer, CertificateSerializer, CourseEnrollmentSerializer, CourseSerializer, LearningPathSerializer, LearningRecommendationSerializer, LessonProgressSerializer, LessonSerializer, QuizAttemptSerializer, QuizSerializer, UserLearningSignalSerializer
from .services import LearningService


class LearningPathViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LearningPathSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = LearningPath.objects.all()


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "slug"

    def get_queryset(self):
        return Course.objects.filter(is_published=True).select_related("path").prefetch_related("modules", "modules__lessons")

    @action(detail=True, methods=["post"])
    def enroll(self, request, slug=None):
        course = self.get_object()
        enrollment, _ = CourseEnrollment.objects.get_or_create(user=request.user, course=course)
        return Response(CourseEnrollmentSerializer(enrollment).data)


class LessonViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Lesson.objects.select_related("module", "module__course").prefetch_related("resources")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        lesson = self.get_object()
        progress = LearningService.complete_lesson(
            request.user,
            lesson,
            time_spent_seconds=request.data.get("time_spent_seconds", 0),
            notes=request.data.get("notes", ""),
        )
        return Response(LessonProgressSerializer(progress).data)


class LessonProgressViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LessonProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LessonProgress.objects.filter(user=self.request.user).select_related("lesson")


class QuizViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Quiz.objects.prefetch_related("questions").select_related("lesson")

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        quiz = self.get_object()
        answers = request.data.get("answers", {})
        total = quiz.questions.count() or 1
        correct = 0
        for question in quiz.questions.all():
            if str(answers.get(str(question.id))) == str(question.correct_answer.get("value")):
                correct += 1
        score = round((correct / total) * 100, 2)
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            answers=answers,
            score=score,
            passed=score >= quiz.pass_score,
            completed_at=timezone.now(),
        )
        if attempt.passed:
            LearningService.complete_lesson(request.user, quiz.lesson)
        return Response(QuizAttemptSerializer(attempt).data)


class AssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Assignment.objects.select_related("lesson")

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        assignment = self.get_object()
        submission, _ = AssignmentSubmission.objects.update_or_create(
            assignment=assignment,
            user=request.user,
            defaults={
                "linked_model": request.data.get("linked_model", ""),
                "linked_id": request.data.get("linked_id", ""),
                "notes": request.data.get("notes", ""),
                "status": "SUBMITTED",
            },
        )
        return Response(AssignmentSubmissionSerializer(submission).data)


class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user).select_related("course")


class LearningRecommendationViewSet(viewsets.ModelViewSet):
    serializer_class = LearningRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LearningRecommendation.objects.filter(user=self.request.user, is_dismissed=False)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserLearningSignalViewSet(viewsets.ModelViewSet):
    serializer_class = UserLearningSignalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserLearningSignal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        signal = serializer.save(user=self.request.user)
        LearningService.recommend_for_signal(signal)

