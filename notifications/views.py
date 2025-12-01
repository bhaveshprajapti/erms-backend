# notifications/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import FCMToken, Notification
from .serializers import FCMTokenSerializer, NotificationSerializer, SendNotificationSerializer
from .firebase import send_push_notification, send_multicast_notification
import logging

logger = logging.getLogger(__name__)


class FCMTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing FCM tokens
    """
    serializer_class = FCMTokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FCMToken.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Register a new FCM token or update existing one"""
        token = request.data.get('token')
        
        # Check if token already exists
        existing_token = FCMToken.objects.filter(token=token).first()
        
        if existing_token:
            # Update existing token - reassign to current user and activate
            existing_token.user = request.user
            existing_token.is_active = True
            existing_token.device_type = request.data.get('device_type', existing_token.device_type)
            existing_token.device_name = request.data.get('device_name', existing_token.device_name)
            existing_token.save()
            
            serializer = self.get_serializer(existing_token)
            return Response(
                {
                    'status': 'success',
                    'message': 'FCM token updated successfully',
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        # Create new token
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                'status': 'success',
                'message': 'FCM token registered successfully',
                'data': serializer.data
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    @action(detail=False, methods=['post'])
    def deactivate(self, request):
        """Deactivate a specific token"""
        token = request.data.get('token')
        
        if not token:
            return Response(
                {'status': 'error', 'message': 'Token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            fcm_token = FCMToken.objects.get(token=token, user=request.user)
            fcm_token.is_active = False
            fcm_token.save()
            
            return Response(
                {
                    'status': 'success',
                    'message': 'Token deactivated successfully'
                },
                status=status.HTTP_200_OK
            )
        except FCMToken.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'Token not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notifications
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        serializer = self.get_serializer(notification)
        return Response(
            {
                'status': 'success',
                'message': 'Notification marked as read',
                'data': serializer.data
            }
        )

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read"""
        updated = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        return Response(
            {
                'status': 'success',
                'message': f'{updated} notifications marked as read'
            }
        )

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return Response(
            {
                'status': 'success',
                'unread_count': count
            }
        )

    @action(detail=False, methods=['post'])
    def send_notification(self, request):
        """
        Send push notification to users
        (Admin only - you may want to add permission check)
        """
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        user_ids = data.get('user_ids', [])
        title = data['title']
        body = data['body']
        notification_type = data.get('notification_type', 'info')
        extra_data = data.get('data', {})
        
        # Get FCM tokens for specified users
        if user_ids:
            fcm_tokens = FCMToken.objects.filter(
                user_id__in=user_ids,
                is_active=True
            )
        else:
            fcm_tokens = FCMToken.objects.filter(is_active=True)
        
        if not fcm_tokens.exists():
            return Response(
                {
                    'status': 'error',
                    'message': 'No active FCM tokens found for the specified users'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Prepare notification data
        notification_data = {
            'type': notification_type,
            'timestamp': str(timezone.now()),
            **extra_data
        }
        
        # Send notifications
        tokens = [token.token for token in fcm_tokens]
        response = send_multicast_notification(tokens, title, body, notification_data)
        
        # Save notification history
        for fcm_token in fcm_tokens:
            Notification.objects.create(
                user=fcm_token.user,
                title=title,
                body=body,
                notification_type=notification_type,
                data=extra_data
            )
        
        if response:
            return Response(
                {
                    'status': 'success',
                    'message': f'Notification sent to {response.success_count} devices',
                    'success_count': response.success_count,
                    'failure_count': response.failure_count
                }
            )
        else:
            return Response(
                {
                    'status': 'error',
                    'message': 'Failed to send notifications'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
