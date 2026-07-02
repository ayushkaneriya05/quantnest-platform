import uuid

from django.utils import timezone

from gamification.services import GamificationService
from platform_events.services import ActivityService, DomainEventService

from .models import Certificate, CourseEnrollment, LessonProgress, LearningRecommendation


class LearningService:
    @staticmethod
    def complete_lesson(user, lesson, time_spent_seconds=0, notes=""):
        progress, _ = LessonProgress.objects.get_or_create(user=user, lesson=lesson)
        progress.is_completed = True
        progress.completed_at = progress.completed_at or timezone.now()
        progress.time_spent_seconds += int(time_spent_seconds or 0)
        progress.notes = notes or progress.notes
        progress.save()
        event = DomainEventService.emit("LESSON_COMPLETED", user=user, source=lesson, source_app="learning", payload={"lesson": lesson.title})
        ActivityService.create(user, "LESSON_COMPLETED", f"Completed {lesson.title}", target=lesson, domain_event=event, metadata={"course": lesson.module.course.title})
        GamificationService.grant_xp(user, "LESSON_COMPLETED", 15, source=lesson)
        LearningService.refresh_course_progress(user, lesson.module.course)
        return progress

    @staticmethod
    def refresh_course_progress(user, course):
        lessons = course.modules.prefetch_related("lessons")
        lesson_ids = [lesson.id for module in lessons for lesson in module.lessons.all()]
        if not lesson_ids:
            return None
        completed = LessonProgress.objects.filter(user=user, lesson_id__in=lesson_ids, is_completed=True).count()
        pct = round((completed / len(lesson_ids)) * 100, 2)
        enrollment, _ = CourseEnrollment.objects.get_or_create(user=user, course=course)
        enrollment.progress_pct = pct
        if pct >= 100 and not enrollment.completed_at:
            enrollment.completed_at = timezone.now()
            Certificate.objects.get_or_create(
                user=user,
                course=course,
                defaults={"certificate_code": f"QN-{course.id}-{user.id}-{uuid.uuid4().hex[:8].upper()}"},
            )
            GamificationService.grant_xp(user, "COURSE_COMPLETED", 100, source=course)
        enrollment.save()
        return enrollment

    @staticmethod
    def recommend_for_signal(signal):
        title = "Review risk discipline" if signal.signal_type in {"STOP_LOSS_VIOLATION", "RISK_ISSUE"} else "Continue targeted practice"
        return LearningRecommendation.objects.create(
            user=signal.user,
            recommendation_type="COURSE",
            title=title,
            reason=f"Recommended from signal: {signal.get_signal_type_display()}",
            priority="HIGH" if signal.strength >= 3 else "MEDIUM",
            metadata={"signal_type": signal.signal_type},
        )

