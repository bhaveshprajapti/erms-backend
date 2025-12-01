# notifications/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count, Q
from .models import FCMToken, Notification
from .serializers import (
    FCMTokenSerializer, 
    NotificationSerializer, 
    SendNotificationSerializer,
    FCMTokenAdminSerializer,
    NotificationLogSerializer
)
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

    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        """Delete all notifications for the current user"""
        deleted_count, _ = Notification.objects.filter(user=request.user).delete()
        return Response(
            {
                'status': 'success',
                'message': f'Deleted {deleted_count} notifications'
            }
        )

    @action(detail=False, methods=['delete'])
    def clear_today(self, request):
        """Delete today's notifications for the current user"""
        from datetime import datetime
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        deleted_count, _ = Notification.objects.filter(
            user=request.user,
            sent_at__gte=today_start
        ).delete()
        return Response(
            {
                'status': 'success',
                'message': f'Deleted {deleted_count} notifications from today'
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
            fcm_tokens = list(FCMToken.objects.filter(
                user_id__in=user_ids,
                is_active=True
            ))
        else:
            fcm_tokens = list(FCMToken.objects.filter(is_active=True))
        
        if not fcm_tokens:
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
        
        # Send notifications and handle invalid tokens
        tokens = [token.token for token in fcm_tokens]
        response, invalid_tokens = send_multicast_notification(tokens, title, body, notification_data)
        
        # Deactivate invalid/expired tokens
        if invalid_tokens:
            FCMToken.objects.filter(token__in=invalid_tokens).update(is_active=False)
            logger.info(f"Deactivated {len(invalid_tokens)} invalid FCM tokens")
        
        # Save notification history - only for users with valid tokens
        valid_token_set = set(tokens) - set(invalid_tokens) if invalid_tokens else set(tokens)
        users_notified = set()
        for fcm_token in fcm_tokens:
            if fcm_token.token in valid_token_set and fcm_token.user_id not in users_notified:
                Notification.objects.create(
                    user=fcm_token.user,
                    title=title,
                    body=body,
                    notification_type=notification_type,
                    data=extra_data
                )
                users_notified.add(fcm_token.user_id)
        
        if response:
            return Response(
                {
                    'status': 'success',
                    'message': f'Notification sent to {response.success_count} devices',
                    'success_count': response.success_count,
                    'failure_count': response.failure_count,
                    'invalid_tokens_removed': len(invalid_tokens) if invalid_tokens else 0
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


class AdminNotificationViewSet(viewsets.ModelViewSet):
    """
    Admin ViewSet for managing all notifications and FCM tokens
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_serializer_class(self):
        if self.action in ['tokens', 'delete_token', 'cleanup_tokens']:
            return FCMTokenAdminSerializer
        return NotificationLogSerializer
    
    def get_queryset(self):
        return Notification.objects.all().select_related('user').order_by('-sent_at')
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics"""
        total_notifications = Notification.objects.count()
        unread_notifications = Notification.objects.filter(is_read=False).count()
        total_tokens = FCMToken.objects.count()
        active_tokens = FCMToken.objects.filter(is_active=True).count()
        
        # Get notifications by type
        by_type = Notification.objects.values('notification_type').annotate(
            count=Count('id')
        )
        
        # Get tokens by device type
        by_device = FCMToken.objects.filter(is_active=True).values('device_type').annotate(
            count=Count('id')
        )
        
        return Response({
            'total_notifications': total_notifications,
            'unread_notifications': unread_notifications,
            'total_tokens': total_tokens,
            'active_tokens': active_tokens,
            'inactive_tokens': total_tokens - active_tokens,
            'notifications_by_type': list(by_type),
            'tokens_by_device': list(by_device)
        })
    
    @action(detail=False, methods=['get'])
    def tokens(self, request):
        """Get all FCM tokens with user info"""
        tokens = FCMToken.objects.all().select_related('user').order_by('-created_at')
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter == 'active':
            tokens = tokens.filter(is_active=True)
        elif status_filter == 'inactive':
            tokens = tokens.filter(is_active=False)
        
        # Filter by device type
        device_type = request.query_params.get('device_type')
        if device_type:
            tokens = tokens.filter(device_type=device_type)
        
        serializer = FCMTokenAdminSerializer(tokens, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['delete'], url_path='tokens/(?P<token_id>[^/.]+)')
    def delete_token(self, request, token_id=None):
        """Delete a specific FCM token"""
        try:
            token = FCMToken.objects.get(id=token_id)
            token.delete()
            return Response({
                'status': 'success',
                'message': 'Token deleted successfully'
            })
        except FCMToken.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Token not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def cleanup_tokens(self, request):
        """Remove all inactive tokens"""
        deleted_count, _ = FCMToken.objects.filter(is_active=False).delete()
        return Response({
            'status': 'success',
            'message': f'Deleted {deleted_count} inactive tokens'
        })
    
    @action(detail=False, methods=['get'])
    def logs(self, request):
        """Get notification logs with filtering"""
        notifications = self.get_queryset()
        
        # Filter by user
        user_id = request.query_params.get('user_id')
        if user_id:
            notifications = notifications.filter(user_id=user_id)
        
        # Filter by type
        notification_type = request.query_params.get('type')
        if notification_type:
            notifications = notifications.filter(notification_type=notification_type)
        
        # Filter by read status
        is_read = request.query_params.get('is_read')
        if is_read is not None:
            notifications = notifications.filter(is_read=is_read.lower() == 'true')
        
        # Filter by date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            notifications = notifications.filter(sent_at__gte=start_date)
        if end_date:
            notifications = notifications.filter(sent_at__lte=end_date)
        
        serializer = NotificationLogSerializer(notifications[:100], many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['delete'])
    def clear_old(self, request):
        """Clear notifications older than specified days"""
        from datetime import timedelta
        days = int(request.query_params.get('days', 30))
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count, _ = Notification.objects.filter(sent_at__lt=cutoff_date).delete()
        return Response({
            'status': 'success',
            'message': f'Deleted {deleted_count} notifications older than {days} days'
        })
