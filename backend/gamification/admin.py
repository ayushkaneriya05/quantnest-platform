from django.contrib import admin

from .models import Achievement, AntiGamingRule, Challenge, ChallengeParticipant, LeaderboardSnapshot, Streak, UserAchievement, UserTrustFlag, UserXPBalance, XPEvent, XPGrantLimit


admin.site.register(XPGrantLimit)
admin.site.register(XPEvent)
admin.site.register(UserXPBalance)
admin.site.register(Achievement)
admin.site.register(UserAchievement)
admin.site.register(Streak)
admin.site.register(Challenge)
admin.site.register(ChallengeParticipant)
admin.site.register(LeaderboardSnapshot)
admin.site.register(UserTrustFlag)
admin.site.register(AntiGamingRule)
