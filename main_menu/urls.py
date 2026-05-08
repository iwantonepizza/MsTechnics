from django.urls import path
from main_menu import views

app_name = 'main_menu'

urlpatterns = [
    path('', views.index, name='index'),
    path('get-application-color-info/', views.get_application_color_info, name='application_color_info'),
    path('panel-condition-confirm/', views.panel_condition_confirm, name='panel_condition_confirm'),
    path('modal-create-application/', views.create_application_confirm, name='create_application_confirm'),

]
