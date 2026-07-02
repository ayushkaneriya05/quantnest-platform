from django.contrib import admin

from .models import Assignment, AssignmentSubmission, Certificate, Course, CourseEnrollment, CourseModule, LearningPath, LearningRecommendation, Lesson, LessonProgress, LessonResource, Quiz, QuizAttempt, QuizQuestion, UserLearningSignal


admin.site.register(LearningPath)
admin.site.register(Course)
admin.site.register(CourseModule)
admin.site.register(Lesson)
admin.site.register(LessonResource)
admin.site.register(CourseEnrollment)
admin.site.register(LessonProgress)
admin.site.register(Quiz)
admin.site.register(QuizQuestion)
admin.site.register(QuizAttempt)
admin.site.register(Assignment)
admin.site.register(AssignmentSubmission)
admin.site.register(Certificate)
admin.site.register(UserLearningSignal)
admin.site.register(LearningRecommendation)
