from django.contrib import admin
from .models import FileDrop, Room, RoomMessage

@admin.register(FileDrop)
class FileDropAdmin(admin.ModelAdmin):
    list_display = ('pin', 'original_filename', 'expires_hours', 'one_time', 'download_count', 'created_at')
    readonly_fields = ('pin', 'created_at', 'download_count')
    ordering = ('-created_at',)

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('code', 'created_at', 'expires_hours')
    readonly_fields = ('code', 'created_at')

@admin.register(RoomMessage)
class RoomMessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'sender_name', 'created_at')
    readonly_fields = ('created_at',)
