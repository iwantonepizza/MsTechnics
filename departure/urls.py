from django.urls import path, include
from departure.views import *

app_name = 'departure'

urlpatterns = [
    path('', index, name='index'),
    path('<int:task_id>/', create, name='create'),
    path('create/', create, name='create'),
    path('complete/', complete, name='complete'),
    path('delete/', delete, name='delete'),
]
