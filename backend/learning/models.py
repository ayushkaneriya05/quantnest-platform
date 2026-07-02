from django.conf import settings
from django.db import models

from common.models import BaseTimestampModel


class LearningPath(BaseTimestampModel):
    LEVELS = [("BEGINNER", "Beginner"), ("INTERMEDIATE", "Intermediate"), ("ADVANCED", "Advanced")]

    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    level = models.CharField(max_length=20, choices=LEVELS, default="BEGINNER")
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "learning_path"
        ordering = ["sort_order", "title"]


class Course(BaseTimestampModel):
    CATEGORIES = [
        ("TRADING_FOUNDATIONS", "Trading Foundations"),
        ("TECHNICAL_ANALYSIS", "Technical Analysis"),
        ("RISK_MANAGEMENT", "Risk Management"),
        ("PSYCHOLOGY", "Psychology"),
        ("STRATEGY_BUILDING", "Strategy Building"),
        ("BACKTESTING", "Backtesting"),
        ("AUTOMATION", "Automation"),
        ("MARKETPLACE_CREATOR", "Marketplace Creator"),
    ]
    LEVELS = LearningPath.LEVELS

    path = models.ForeignKey(LearningPath, on_delete=models.SET_NULL, null=True, blank=True, related_name="courses")
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=40, choices=CATEGORIES)
    level = models.CharField(max_length=20, choices=LEVELS, default="BEGINNER")
    estimated_minutes = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    prerequisites = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="unlocks")

    class Meta:
        db_table = "learning_course"
        ordering = ["category", "level", "title"]


class CourseModule(BaseTimestampModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "learning_course_module"
        ordering = ["course", "sort_order"]


class Lesson(BaseTimestampModel):
    LESSON_TYPES = [("ARTICLE", "Article"), ("VIDEO", "Video"), ("QUIZ", "Quiz"), ("LAB", "Lab"), ("REPLAY", "Replay"), ("ASSIGNMENT", "Assignment")]

    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=180)
    lesson_type = models.CharField(max_length=20, choices=LESSON_TYPES, default="ARTICLE")
    content = models.TextField(blank=True)
    estimated_minutes = models.PositiveIntegerField(default=0)
    sort_order = models.PositiveIntegerField(default=0)
    required_for_certificate = models.BooleanField(default=True)

    class Meta:
        db_table = "learning_lesson"
        ordering = ["module", "sort_order"]


class LessonResource(BaseTimestampModel):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="resources")
    title = models.CharField(max_length=160)
    resource_type = models.CharField(max_length=40, default="LINK")
    url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "learning_lesson_resource"


class CourseEnrollment(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="course_enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    progress_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "learning_course_enrollment"
        unique_together = ["user", "course"]
        ordering = ["-updated_at"]


class LessonProgress(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "learning_lesson_progress"
        unique_together = ["user", "lesson"]


class Quiz(BaseTimestampModel):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name="quiz")
    title = models.CharField(max_length=160)
    pass_score = models.PositiveIntegerField(default=70)
    max_attempts = models.PositiveIntegerField(default=3)

    class Meta:
        db_table = "learning_quiz"


class QuizQuestion(BaseTimestampModel):
    QUESTION_TYPES = [("SINGLE", "Single Choice"), ("MULTIPLE", "Multiple Choice"), ("CHART", "Chart Identification"), ("NUMERIC", "Numeric")]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default="SINGLE")
    prompt = models.TextField()
    options = models.JSONField(default=list, blank=True)
    correct_answer = models.JSONField(default=dict, blank=True)
    explanation = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "learning_quiz_question"
        ordering = ["quiz", "sort_order"]


class QuizAttempt(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    answers = models.JSONField(default=dict, blank=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    passed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "learning_quiz_attempt"
        ordering = ["-created_at"]


class Assignment(BaseTimestampModel):
    ASSIGNMENT_TYPES = [("JOURNAL", "Journal"), ("BACKTEST", "Backtest"), ("STRATEGY", "Strategy"), ("PAPER_TRADE", "Paper Trade"), ("RISK_REVIEW", "Risk Review"), ("REPLAY", "Replay")]

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=160)
    assignment_type = models.CharField(max_length=30, choices=ASSIGNMENT_TYPES)
    instructions = models.TextField(blank=True)
    required_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "learning_assignment"


class AssignmentSubmission(BaseTimestampModel):
    STATUSES = [("SUBMITTED", "Submitted"), ("APPROVED", "Approved"), ("NEEDS_WORK", "Needs Work")]

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assignment_submissions")
    linked_model = models.CharField(max_length=80, blank=True)
    linked_id = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="SUBMITTED")
    feedback = models.TextField(blank=True)

    class Meta:
        db_table = "learning_assignment_submission"
        unique_together = ["assignment", "user"]


class Certificate(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificates")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="certificates")
    certificate_code = models.CharField(max_length=80, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "learning_certificate"
        unique_together = ["user", "course"]
        ordering = ["-issued_at"]


class UserLearningSignal(BaseTimestampModel):
    SIGNAL_TYPES = [
        ("REPEATED_MISTAKE", "Repeated Mistake"),
        ("REVENGE_TRADING", "Revenge Trading"),
        ("OVERTRADING", "Overtrading"),
        ("STOP_LOSS_VIOLATION", "Stop Loss Violation"),
        ("RISK_ISSUE", "Risk Issue"),
        ("EMOTIONAL_PATTERN", "Emotional Pattern"),
        ("QUIZ_GAP", "Quiz Gap"),
        ("STRATEGY_GAP", "Strategy Gap"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learning_signals")
    signal_type = models.CharField(max_length=40, choices=SIGNAL_TYPES)
    strength = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    source_model = models.CharField(max_length=80, blank=True)
    source_id = models.CharField(max_length=80, blank=True)
    details = models.JSONField(default=dict, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "learning_user_signal"
        ordering = ["-created_at"]


class LearningRecommendation(BaseTimestampModel):
    RECOMMENDATION_TYPES = [("LESSON", "Lesson"), ("COURSE", "Course"), ("QUIZ", "Quiz"), ("ASSIGNMENT", "Assignment"), ("CHALLENGE", "Challenge"), ("JOURNAL_PROMPT", "Journal Prompt")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learning_recommendations")
    recommendation_type = models.CharField(max_length=30, choices=RECOMMENDATION_TYPES)
    title = models.CharField(max_length=180)
    reason = models.TextField(blank=True)
    target_model = models.CharField(max_length=80, blank=True)
    target_id = models.CharField(max_length=80, blank=True)
    priority = models.CharField(max_length=20, default="MEDIUM")
    is_dismissed = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "learning_recommendation"
        ordering = ["-created_at"]

