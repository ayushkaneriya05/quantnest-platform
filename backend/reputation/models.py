from django.conf import settings
from django.db import models

from common.models import BaseTimestampModel


class TraderReputationProfile(BaseTimestampModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trader_reputation")
    credibility_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    consistency_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    discipline_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    transparency_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    risk_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    sample_size_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    journal_honesty_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    strategy_survival_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    drawdown_discipline_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    rule_follow_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    max_drawdown_pct = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    sharpe_ratio = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    sample_size = models.PositiveIntegerField(default=0)
    manipulation_flags = models.JSONField(default=list, blank=True)
    last_calculated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "reputation_trader_profile"
        ordering = ["-credibility_score"]


class ReputationScore(BaseTimestampModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reputation_scores")
    score_type = models.CharField(max_length=80)
    score = models.DecimalField(max_digits=8, decimal_places=2)
    inputs = models.JSONField(default=dict, blank=True)
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reputation_score"
        ordering = ["-calculated_at"]


class TradingProof(BaseTimestampModel):
    PROOF_TYPES = [("BROKER_VERIFIED", "Broker Verified"), ("PAPER_VERIFIED", "Paper Verified"), ("TIMESTAMP_VERIFIED", "Timestamp Verified")]
    STATUSES = [("PENDING", "Pending"), ("VERIFIED", "Verified"), ("REJECTED", "Rejected"), ("REVOKED", "Revoked")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trading_proofs")
    proof_type = models.CharField(max_length=40, choices=PROOF_TYPES)
    source_model = models.CharField(max_length=80)
    source_id = models.CharField(max_length=80)
    verification_hash = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="PENDING")
    verified_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "reputation_trading_proof"
        unique_together = ["proof_type", "source_model", "source_id"]
        ordering = ["-created_at"]


class BacktestProof(BaseTimestampModel):
    STATUSES = TradingProof.STATUSES

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="backtest_proofs")
    backtest_run = models.ForeignKey("backtesting.BacktestRun", on_delete=models.CASCADE, related_name="proofs")
    reproducibility_hash = models.CharField(max_length=128)
    parameters_snapshot = models.JSONField(default=dict, blank=True)
    result_snapshot = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="PENDING")
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "reputation_backtest_proof"
        unique_together = ["backtest_run", "reproducibility_hash"]


class StrategyVerification(BaseTimestampModel):
    VERIFICATION_TYPES = [("BACKTEST_REPRODUCIBLE", "Backtest Reproducible"), ("STRATEGY_EXECUTION_VERIFIED", "Strategy Execution Verified"), ("TRANSPARENCY_VERIFIED", "Transparency Verified")]
    STATUSES = TradingProof.STATUSES

    strategy = models.ForeignKey("strategies.Strategy", on_delete=models.CASCADE, related_name="verifications")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="strategy_verifications")
    verification_type = models.CharField(max_length=40, choices=VERIFICATION_TYPES)
    status = models.CharField(max_length=20, choices=STATUSES, default="PENDING")
    transparency_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    evidence = models.JSONField(default=dict, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "reputation_strategy_verification"
        unique_together = ["strategy", "verification_type"]


class TradeReplay(BaseTimestampModel):
    VISIBILITIES = [("PUBLIC", "Public"), ("FOLLOWERS", "Followers"), ("PRIVATE", "Private")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trade_replays")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    source_model = models.CharField(max_length=80, blank=True)
    source_id = models.CharField(max_length=80, blank=True)
    chart_state_json = models.JSONField(default=dict, blank=True)
    indicator_state = models.JSONField(default=dict, blank=True)
    drawing_state = models.JSONField(default=dict, blank=True)
    candles_snapshot = models.JSONField(default=list, blank=True)
    execution_markers = models.JSONField(default=list, blank=True)
    journal_context = models.JSONField(default=dict, blank=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITIES, default="PRIVATE")
    is_immutable = models.BooleanField(default=False)

    class Meta:
        db_table = "reputation_trade_replay"
        ordering = ["-created_at"]


class AIModerationFlag(BaseTimestampModel):
    FLAG_TYPES = [("SPAM", "Spam"), ("FAKE_PNL", "Fake PnL"), ("ABUSE", "Abuse"), ("PUMP_DUMP", "Pump And Dump"), ("REFERRAL_SPAM", "Referral Spam"), ("SUSPICIOUS_PROMOTION", "Suspicious Promotion")]
    STATUSES = [("OPEN", "Open"), ("REVIEWING", "Reviewing"), ("RESOLVED", "Resolved"), ("DISMISSED", "Dismissed")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="ai_moderation_flags")
    content_type = models.CharField(max_length=80)
    object_id = models.CharField(max_length=80)
    flag_type = models.CharField(max_length=40, choices=FLAG_TYPES)
    confidence = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    reason = models.TextField(blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="OPEN")

    class Meta:
        db_table = "reputation_ai_moderation_flag"
        ordering = ["-created_at"]


class MentorProfile(BaseTimestampModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mentor_profile")
    headline = models.CharField(max_length=180, blank=True)
    specialties = models.JSONField(default=list, blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="INR")
    is_accepting_sessions = models.BooleanField(default=False)
    verified_mentor = models.BooleanField(default=False)

    class Meta:
        db_table = "reputation_mentor_profile"


class OfficeHourSession(BaseTimestampModel):
    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE, related_name="office_hours")
    title = models.CharField(max_length=180)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(default=10)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "reputation_office_hour_session"
        ordering = ["starts_at"]


class MentorshipBooking(BaseTimestampModel):
    STATUSES = [("REQUESTED", "Requested"), ("CONFIRMED", "Confirmed"), ("COMPLETED", "Completed"), ("CANCELLED", "Cancelled")]

    mentor = models.ForeignKey(MentorProfile, on_delete=models.CASCADE, related_name="bookings")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mentorship_bookings")
    session = models.ForeignKey(OfficeHourSession, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings")
    status = models.CharField(max_length=20, choices=STATUSES, default="REQUESTED")
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "reputation_mentorship_booking"

