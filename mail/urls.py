from django.urls import path, include
from mail import views

app_name = 'mail'

urlpatterns = [
    path('auth/', views.google_auth, name='google_auth'),
    path('oauth2callback/', views.oauth2callback, name='oauth2callback'),
    path('emails/', views.get_emails, name='get_emails'),  # Добавим позже
]