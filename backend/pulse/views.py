from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .services import get_daily_pulse
from .serializers import PulseResponseSerializer

class DailyPulseView(APIView):
    permission_classes = [AllowAny]  # or IsAuthenticated if needed

    def get(self, request):
        data = get_daily_pulse()
        return Response(PulseResponseSerializer(data).data)