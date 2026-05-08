from django.urls import path

from .views import max_webhook

app_name = "max"

urlpatterns = [
    path("webhook", max_webhook, name="webhook"),
]
