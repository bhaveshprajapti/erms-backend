# notifications/admin.py
from django.contrib import admin
from .models import FCMToken, Notification


@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_type', 'device_name', 'is_active', 'created_at')
    list_filter = ('device_type', 'is_active', 'created_at')
    search_fields = ('user__username', 'user__email', 'token', 'device_name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'sent_at')
    list_filter = ('notification_type', 'is_read', 'sent_at')
    search_fields = ('user__username', 'user__email', 'title', 'body')
    readonly_fields = ('sent_at', 'read_at')
    ordering = ('-sent_at',)
