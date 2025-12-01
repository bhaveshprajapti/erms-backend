# notifications/models.py
from django.db import models
from django.conf import settings


class FCMToken(models.Model):
    """
    Model to store Firebase Cloud Messaging tokens for users
    """
    DEVICE_TYPES = [
        ('web', 'Web Browser'),
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('windows', 'Windows'),
        ('mac', 'Mac'),
        ('linux', 'Linux'),
        ('unknown', 'Unknown'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fcm_tokens'
    )
    token = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES, default='web')
    device_name = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fcm_tokens'
        verbose_name = 'FCM Token'
        verbose_name_plural = 'FCM Tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['token']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.device_type} ({self.token[:20]}...)"


class Notification(models.Model):
    """
    Model to store notification history
    """
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('success', 'Success'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    data = models.JSONField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['sent_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"
