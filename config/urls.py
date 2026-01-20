from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('apps.users.urls')),
    path('pages/', include('apps.pages.urls')),
    path('', include('apps.movies.urls')),
]