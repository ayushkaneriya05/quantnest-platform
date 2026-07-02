from django.db.models import Avg, Count, Q
from django.utils import timezone

from trade_journal.models import JournalEntry

from .models import TraderReputationProfile


class ReputationService:
    @staticmethod
    def recalculate_user(user):
        journals = JournalEntry.objects.filter(user=user)
        total_journals = journals.count()
        rule_follow_rate = 0
        if total_journals:
            rule_follow_rate = journals.filter(rule_followed=True).count() / total_journals * 100
        quality = journals.aggregate(setup=Avg("setup_quality"), execution=Avg("execution_quality"))
        quality_score = (((quality["setup"] or 0) + (quality["execution"] or 0)) / 10) * 100
        sample_size_score = min(total_journals * 4, 100)
        discipline_score = round((rule_follow_rate * 0.7) + (quality_score * 0.3), 2)
        transparency_score = min(total_journals * 5, 100)
        credibility = round((discipline_score * 0.4) + (sample_size_score * 0.25) + (transparency_score * 0.2) + (quality_score * 0.15), 2)
        profile, _ = TraderReputationProfile.objects.get_or_create(user=user)
        profile.credibility_score = credibility
        profile.consistency_score = quality_score
        profile.discipline_score = discipline_score
        profile.transparency_score = transparency_score
        profile.risk_score = rule_follow_rate
        profile.sample_size_score = sample_size_score
        profile.journal_honesty_score = transparency_score
        profile.drawdown_discipline_score = rule_follow_rate
        profile.rule_follow_rate = rule_follow_rate
        profile.sample_size = total_journals
        profile.last_calculated_at = timezone.now()
        profile.save()
        return profile

