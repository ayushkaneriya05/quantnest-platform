from django.contrib import admin

from .models import AIModerationFlag, BacktestProof, MentorProfile, MentorshipBooking, OfficeHourSession, ReputationScore, StrategyVerification, TradeReplay, TraderReputationProfile, TradingProof


admin.site.register(TraderReputationProfile)
admin.site.register(ReputationScore)
admin.site.register(TradingProof)
admin.site.register(BacktestProof)
admin.site.register(StrategyVerification)
admin.site.register(TradeReplay)
admin.site.register(AIModerationFlag)
admin.site.register(MentorProfile)
admin.site.register(OfficeHourSession)
admin.site.register(MentorshipBooking)
