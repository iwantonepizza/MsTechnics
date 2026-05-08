from django.urls import path, include
from application.views import *

app_name = 'application'

urlpatterns = [
    path('', index, name='index'),
    path('<int:application_id>/', index, name='info'),

    path('create-application/', create, name='create'),

    path('modal-next-step/', modal_next_step, name='modal_next_step'),
    path('next_step/', next_step, name='next_step'),

    path('modal-dell-application/', modal_dell_application, name='modal_dell_application'),
    path('delete/', delete, name='delete'),

    path('modal-change-executor/', modal_change_executor, name='modal_change_executor'),
    path('change-executor/', change_executor, name='change_executor'),

]
