from django.urls import path
from .consumers import ResearchConsumer

websocket_urlpatterns = [path("ws/research/", ResearchConsumer.as_asgi())]
