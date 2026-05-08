from django.urls import path, include
from departure.views import *

app_name = 'departure'

urlpatterns = [
    path('', index, name='index'),
    path('create/', create, name='create'),
    path('create-modal/', create_modal, name='create_modal'),

    path('complete/', complete, name='complete'),
    path('complete-modal/', complete_modal, name='complete_modal'),

    path('delete/', delete, name='delete'),
    path('delete-modal/', delete_modal, name='delete_modal'),

    path('change-executor', change_executor, name='change_executor'),
    path('change-executor-modal/', change_executor_modal, name='change_executor_modal'),

    path('archivebate', archivebate, name='archivebate'),
    path('archive-modal/', archive_modal, name='archive_modal'),

    path('<int:task_id>/', index, name='info'),

]
