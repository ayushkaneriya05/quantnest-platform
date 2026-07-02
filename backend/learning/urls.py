from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AssignmentViewSet, CertificateViewSet, CourseViewSet, LearningPathViewSet, LearningRecommendationViewSet, LessonProgressViewSet, LessonViewSet, QuizViewSet, UserLearningSignalViewSet

router = DefaultRouter()
router.register(r"paths", LearningPathViewSet, basename="learning-path")
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"lessons", LessonViewSet, basename="lesson")
router.register(r"progress", LessonProgressViewSet, basename="lesson-progress")
router.register(r"quizzes", QuizViewSet, basename="quiz")
router.register(r"assignments", AssignmentViewSet, basename="assignment")
router.register(r"certificates", CertificateViewSet, basename="certificate")
router.register(r"recommendations", LearningRecommendationViewSet, basename="learning-recommendation")
router.register(r"signals", UserLearningSignalViewSet, basename="learning-signal")

urlpatterns = [path("", include(router.urls))]

