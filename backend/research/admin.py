from django.contrib import admin

from .models import ResearchAction, ResearchRun, ResearchSession

admin.site.register(ResearchSession)
admin.site.register(ResearchRun)
admin.site.register(ResearchAction)
