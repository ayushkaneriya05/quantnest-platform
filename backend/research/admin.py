from django.contrib import admin
from .models import ResearchSession, ResearchRun, ResearchAction

admin.site.register(ResearchSession)
admin.site.register(ResearchRun)
admin.site.register(ResearchAction)
