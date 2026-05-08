from django.urls import path, include
from main import views

app_name = 'main'

urlpatterns = [
    path('', views.index, name='index'),
    path('service/', include('service.urls', namespace='service')),
    path('monitoring/', include('monitoring.urls', namespace='monitoring')),
    path('control/', include('control.urls', namespace='control')),
    path('zip/', include('zip.urls', namespace='zip')),
    path('departure/', include('departure.urls', namespace='departure')),
    path('application/', include('application.urls', namespace='application')),
    path('sys-check/', views.sys_check, name='system_check_page'),
    path('get-contacts/<int:display_id>/', views.get_display_contacts, name='get_display_contacts'),
    path('gmail/', include('mail.urls', namespace='mail')),

]
