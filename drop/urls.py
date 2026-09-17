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
    path('robots.txt', views.robots_txt_view, name='robots_txt'),
    path('sitemap.xml', views.sitemap_xml_view, name='sitemap_xml'),
    
    # Spider-Verse Rooms
    path('room/create/', views.create_room_view, name='create_room'),
    path('room/join/', views.join_room_view, name='join_room'),
    path('room/<str:room_code>/', views.room_chat_view, name='room_chat'),
    path('room/<str:room_code>/send/', views.api_send_message, name='api_send_message'),
    path('room/<str:room_code>/messages/', views.api_get_messages, name='api_get_messages'),
    path('room/<str:room_code>/react/<int:message_id>/', views.api_toggle_reaction, name='api_toggle_reaction'),
    path('room/<str:room_code>/delete/<int:message_id>/', views.api_delete_message, name='api_delete_message'),
    path('room/<str:room_code>/typing/', views.api_typing_indicator, name='api_typing_indicator'),
    
    # PWA
    path('manifest.json', views.manifest_view, name='manifest'),
    path('sw.js', views.service_worker_view, name='service_worker'),
]

handler404 = 'drop.views.custom_404_view'
