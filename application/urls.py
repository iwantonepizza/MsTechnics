from django.urls import path, include
from application.views import *

app_name = 'application'

urlpatterns = [
    path('', index, name='index'),
    path('<int:application_id>/', index, name='info'),
    path('create-application/', create, name='create'),
    path('next_step/', next_step, name='next_step'),
    path('delete/', delete, name='delete'),
]
