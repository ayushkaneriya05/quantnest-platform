from rest_framework.routers import DefaultRouter
from .views import JournalEntryViewSet

router = DefaultRouter()
router.register("entries", JournalEntryViewSet, basename="journal-entry")
urlpatterns = router.urls

