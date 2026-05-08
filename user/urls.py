from django.urls import path
from . import views

app_name = "user"
urlpatterns = [
    path("login/", views.login, name="login"),
    # registration/ УДАЛЁН (SEC-007)
    path("lk/", views.lk, name="lk"),
    path("logout/", views.logout, name="logout"),
]
