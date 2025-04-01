from django.urls import path
from zip import views

app_name = 'zip'

urlpatterns = [
    path('', views.index, name='index'),
    path('add-panel-comment/', views.add_panel_comment, name='add_panel_comment'),
    path('add-panel-comment-modal/', views.add_panel_comment_modal, name='add_panel_comment_modal'),

    path('modal-panel-change-department/', views.modal_panel_change_department, name='modal_panel_change_department'),
    path('panel-change-department/', views.panel_change_department, name='panel_change_department'),

    path('modal-panel-history/', views.panel_info, name="panel_info"),
    path('modal-panel-remove/', views.panel_remove_modal, name="panel_remove_modal"),

    path('wires/update/', views.update_wires, name='update_wires'),
    path('wires/delete-photo/', views.delete_photo, name='delete_photo'),
    path('wires/update-photo/', views.update_photo, name='update_photo'),

    path('upload-photos', views.upload_display_photos, name="upload_display_photos"),
    path('delete-photos/<int:photo_id>/', views.delete_display_photos, name="delete_display_photos"),
    path('get-display-photos/<int:display_id>/', views.get_display_photos, name="get_display_photos"),
    path('<int:panel_id>/', views.index, name='panel_info'),

    path('<slug:display_slug>/', views.index, name='at_display'),

]
