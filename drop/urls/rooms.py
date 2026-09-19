from django.urls import path

from ..views import rooms as views

urlpatterns = [
    path('create/', views.create_room_view, name='create_room'),
    path('join/', views.join_room_view, name='join_room'),
    path('<str:room_code>/', views.room_chat_view, name='room_chat'),
    path('<str:room_code>/send/', views.api_send_message, name='api_send_message'),
    path('<str:room_code>/messages/', views.api_get_messages, name='api_get_messages'),
    path('<str:room_code>/react/<int:message_id>/', views.api_toggle_reaction, name='api_toggle_reaction'),
    path('<str:room_code>/delete/<int:message_id>/', views.api_delete_message, name='api_delete_message'),
    path('<str:room_code>/typing/', views.api_typing_indicator, name='api_typing_indicator'),
]
