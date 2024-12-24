from django.contrib import admin
from django.urls import path, include
from django.urls import include, path
from debug_toolbar.toolbar import debug_toolbar_urls
from MsServiceControl.settings import DEBUG
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
                  path('', include('main.urls', namespace='main')),
                  path('admin/', admin.site.urls),
                  path('menu/', include('main_menu.urls', namespace='main_menu')),
                  path('user/', include('user.urls', namespace='user')),

              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if DEBUG:
    urlpatterns += debug_toolbar_urls()
