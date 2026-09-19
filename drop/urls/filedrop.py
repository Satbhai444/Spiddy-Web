from django.urls import path

from ..views import filedrop as views

urlpatterns = [
    path('upload/', views.upload_view, name='upload'),
    path('upload/success/<str:pin>/', views.success_view, name='upload_success'),
    path('receive/', views.download_view, name='download'),
    path('get/<str:pin>/', views.get_file_view, name='get_file'),
    path('file/<str:pin>/preview/', views.file_preview_view, name='file_preview'),
    path('file/<str:pin>/download/', views.file_download_view, name='file_download'),
]
