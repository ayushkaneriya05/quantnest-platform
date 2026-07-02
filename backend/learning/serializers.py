from rest_framework import serializers

from .models import Assignment, AssignmentSubmission, Certificate, Course, CourseEnrollment, CourseModule, LearningPath, LearningRecommendation, Lesson, LessonProgress, LessonResource, Quiz, QuizAttempt, QuizQuestion, UserLearningSignal


class LearningPathSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningPath
        fields = "__all__"


class LessonResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonResource
        fields = "__all__"


class LessonSerializer(serializers.ModelSerializer):
    resources = LessonResourceSerializer(many=True, read_only=True)

    class Meta:
        model = Lesson
        fields = "__all__"


class CourseModuleSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = CourseModule
        fields = "__all__"


class CourseSerializer(serializers.ModelSerializer):
    path_title = serializers.CharField(source="path.title", read_only=True)
    modules = CourseModuleSerializer(many=True, read_only=True)
    my_progress = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ["id", "path", "path_title", "title", "slug", "description", "category", "level", "estimated_minutes", "is_published", "modules", "my_progress", "created_at", "updated_at"]

    def get_my_progress(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        enrollment = obj.enrollments.filter(user=request.user).first()
        return float(enrollment.progress_pct) if enrollment else 0


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = CourseEnrollment
        fields = "__all__"
        read_only_fields = ["user"]


class LessonProgressSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)

    class Meta:
        model = LessonProgress
        fields = "__all__"
        read_only_fields = ["user", "completed_at"]


class QuizQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        exclude = ["correct_answer"]


class QuizSerializer(serializers.ModelSerializer):
    questions = QuizQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = "__all__"


class QuizAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = "__all__"
        read_only_fields = ["user", "score", "passed", "completed_at"]


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = "__all__"


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)

    class Meta:
        model = AssignmentSubmission
        fields = "__all__"
        read_only_fields = ["user"]


class CertificateSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = Certificate
        fields = "__all__"
        read_only_fields = ["user", "certificate_code", "issued_at"]


class UserLearningSignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLearningSignal
        fields = "__all__"
        read_only_fields = ["user"]


class LearningRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningRecommendation
        fields = "__all__"
        read_only_fields = ["user"]

