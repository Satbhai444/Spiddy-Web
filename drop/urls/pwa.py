from django.urls import path

from ..views import pwa as views

urlpatterns = [
    path('manifest.json', views.manifest_view, name='manifest'),
    path('sw.js', views.service_worker_view, name='service_worker'),
    path('favicon.ico', views.favicon_view, name='favicon'),
]
