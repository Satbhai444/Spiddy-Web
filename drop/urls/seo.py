from django.urls import path

from ..views import seo as views

urlpatterns = [
    path('robots.txt', views.robots_txt_view, name='robots_txt'),
    path('sitemap.xml', views.sitemap_xml_view, name='sitemap_xml'),
]
