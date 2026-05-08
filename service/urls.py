from django.urls import path
from service import views

app_name = 'service'

urlpatterns = [
    path('', views.index, name='index'),
    path('<str:city_name>/<str:display_name>/', views.service_main, name='service_main'),
    path('change-condition/', views.change_condition, name='change_condition'),
    path('change-panel-in-cell/', views.change_panel_in_cell, name='change_panel_in_cell'),
    path('change-panel-modal/', views.change_panel_modal, name='change_panel_modal'),

]
