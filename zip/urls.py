from django.urls import path
from zip import views

app_name = 'zip'

urlpatterns = [
    path('', views.index, name='index'),
    path('search/', views.search, name='search'),
    path('add/<str:id_panel>/', views.add, name='add'),
]
