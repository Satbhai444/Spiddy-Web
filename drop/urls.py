from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('upload/', views.upload_view, name='upload'),
    path('upload/success/<str:pin>/', views.success_view, name='upload_success'),
    path('receive/', views.download_view, name='download'),
    path('get/<str:pin>/', views.get_file_view, name='get_file'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('terms/', views.terms_view, name='terms'),
    path('dmca/', views.dmca_view, name='dmca'),
    path('contact/', views.contact_view, name='contact'),
    path('hq/', views.hq_view, name='hq'),
    path('docs/', views.docs_view, name='docs'),
    path('file/<str:pin>/preview/', views.file_preview_view, name='file_preview'),
    path('file/<str:pin>/download/', views.file_download_view, name='file_download'),
    re_path(r'^.*$', views.custom_404_view, name='404_catchall'),
]

handler404 = 'drop.views.custom_404_view'
