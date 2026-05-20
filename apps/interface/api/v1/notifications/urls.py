from django.urls import path

from .views import NotificationInboxView

urlpatterns = [
    path("notifications/inbox/", NotificationInboxView.as_view(), name="notification-inbox"),
]
