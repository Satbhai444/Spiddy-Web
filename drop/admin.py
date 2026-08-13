from django.contrib import admin
from .models import FileDrop

@admin.register(FileDrop)
class FileDropAdmin(admin.ModelAdmin):
    list_display = ('pin', 'original_filename', 'expires_hours', 'one_time', 'download_count', 'created_at')
    readonly_fields = ('pin', 'created_at', 'download_count')
    ordering = ('-created_at',)
