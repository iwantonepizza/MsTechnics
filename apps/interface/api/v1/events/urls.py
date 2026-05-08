from django.urls import path
from .views import SSEStreamView

urlpatterns = [
    path("events/stream", SSEStreamView.as_view(), name="events-stream"),
]
