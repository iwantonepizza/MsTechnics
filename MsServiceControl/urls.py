from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from service.views import edit_panel_comment
urlpatterns = [
                  path('', include('main.urls', namespace='main')),
                  path('admin/', admin.site.urls),
                  path('menu/', include('main_menu.urls', namespace='main_menu')),
                  path('user/', include('user.urls', namespace='user')),
                  path("api/panel/edit-comment", edit_panel_comment, name="edit_panel_comment"),

              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
