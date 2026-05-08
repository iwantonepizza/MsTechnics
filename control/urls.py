from django.urls import path, include
from control import views

app_name = 'control'

urlpatterns = [
    path('', views.index_control, name='index'),
    path('<str:city_name>/<str:display_name>/', views.control_main, name='control_main'),

]
