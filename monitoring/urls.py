from django.urls import path
from monitoring import views

app_name = 'monitoring'

urlpatterns = [
    path('', views.index_monitoring, name='index'),
    path('<str:city_name>/<str:display_name>/', views.monitoring_main, name='monitoring_main'),
]
