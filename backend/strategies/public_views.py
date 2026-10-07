from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Strategy
from .services import StrategySnapshotService
from .snapshots import public_configuration


class SharedStrategyView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, pk):
        strategy = get_object_or_404(Strategy.objects.filter(visibility="PUBLIC"), pk=pk)
        snapshot = public_configuration(StrategySnapshotService._serialize_strategy(strategy))
        response = Response({"configuration": snapshot, "updated_at": strategy.updated_at})
        response["Cache-Control"] = "no-store"
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response
