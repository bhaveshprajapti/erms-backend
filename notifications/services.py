# notifications/services.py
"""
Notification service for sending push notifications across the application.
"""
import logging
from django.utils import timezone
from .models import FCMToken, Notification
from .firebase import send_multicast_notification

logger = logging.getLogger(__name__)


class NotificationService:
    """Service class for sending notifications"""
    
    @staticmethod
    def send_to_user(user, title, body, notification_type='info', data=None):
        """
        Send notification to a specific user
        
        Args:
            user: User object
            title: Notification title
            body: Notification body
            notification_type: Type of notification (info, warning, error, success)
            data: Additional data dict
        
        Returns:
            dict with success status and counts
        """
        tokens = list(FCMToken.objects.filter(user=user, is_active=True))
        
        if not tokens:
            logger.info(f"No active FCM tokens for user {user.username}")
            return {'success': False, 'message': 'No active tokens'}
        
        # Prepare notification data
        notification_data = {
            'type': notification_type,
            'timestamp': str(timezone.now()),
            **(data or {})
        }
        
        # Send push notification
        token_strings = [t.token for t in tokens]
        response, invalid_tokens = send_multicast_notification(
            token_strings, title, body, notification_data
        )
        
        # Deactivate invalid tokens
        if invalid_tokens:
            FCMToken.objects.filter(token__in=invalid_tokens).update(is_active=False)
        
        # Save notification to database
        Notification.objects.create(
            user=user,
            title=title,
            body=body,
            notification_type=notification_type,
            data=data
        )
        
        if response:
            return {
                'success': True,
                'success_count': response.success_count,
                'failure_count': response.failure_count
            }
        return {'success': False, 'message': 'Failed to send'}
    
    @staticmethod
    def send_to_users(users, title, body, notification_type='info', data=None):
        """
        Send notification to multiple users
        
        Args:
            users: List of User objects or queryset
            title: Notification title
            body: Notification body
            notification_type: Type of notification
            data: Additional data dict
        
        Returns:
            dict with success status and counts
        """
        user_ids = [u.id for u in users]
        logger.info(f"send_to_users called: {len(user_ids)} users, title={title}")
        
        tokens = list(FCMToken.objects.filter(user_id__in=user_ids, is_active=True))
        logger.info(f"Found {len(tokens)} active FCM tokens for {len(user_ids)} users")
        
        if not tokens:
            logger.info("No active FCM tokens for specified users")
            return {'success': False, 'message': 'No active tokens'}
        
        # Prepare notification data
        notification_data = {
            'type': notification_type,
            'timestamp': str(timezone.now()),
            **(data or {})
        }
        
        # Send push notification
        token_strings = [t.token for t in tokens]
        response, invalid_tokens = send_multicast_notification(
            token_strings, title, body, notification_data
        )
        
        # Deactivate invalid tokens
        if invalid_tokens:
            FCMToken.objects.filter(token__in=invalid_tokens).update(is_active=False)
        
        # Save notification to database for each user (deduplicated)
        users_notified = set()
        for token in tokens:
            if token.user_id not in users_notified:
                Notification.objects.create(
                    user=token.user,
                    title=title,
                    body=body,
                    notification_type=notification_type,
                    data=data
                )
                users_notified.add(token.user_id)
        
        if response:
            return {
                'success': True,
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'users_notified': len(users_notified)
            }
        return {'success': False, 'message': 'Failed to send'}
    
    @staticmethod
    def send_to_admins(title, body, notification_type='info', data=None):
        """
        Send notification to all admin/staff users
        
        Args:
            title: Notification title
            body: Notification body
            notification_type: Type of notification
            data: Additional data dict
        
        Returns:
            dict with success status and counts
        """
        from accounts.models import User
        from django.db.models import Q
        admins = User.objects.filter(is_active=True).filter(
            Q(is_staff=True) | Q(is_superuser=True)
        )
        return NotificationService.send_to_users(admins, title, body, notification_type, data)
    
    @staticmethod
    def send_to_all_employees(title, body, notification_type='info', data=None):
        """
        Send notification to all active employees (non-admin users)
        
        Args:
            title: Notification title
            body: Notification body
            notification_type: Type of notification
            data: Additional data dict
        
        Returns:
            dict with success status and counts
        """
        from accounts.models import User
        employees = User.objects.filter(
            is_active=True,
            is_staff=False,
            is_superuser=False
        )
        return NotificationService.send_to_users(employees, title, body, notification_type, data)
    
    # ============ Specific Notification Methods ============
    
    @staticmethod
    def notify_announcement(announcement, exclude_user=None):
        """Send notification for a new active announcement to employees only"""
        from accounts.models import User
        from django.utils.timezone import now
        
        # Only send if announcement is currently active
        today = now().date()
        logger.info(f"notify_announcement called: title={announcement.title}, start={announcement.start_date}, end={announcement.end_date}, today={today}")
        
        if announcement.start_date <= today <= announcement.end_date:
            # Send only to active employees (non-admin, non-staff users)
            employees = User.objects.filter(
                is_active=True,
                is_staff=False,
                is_superuser=False
            )
            
            employee_count = employees.count()
            logger.info(f"Found {employee_count} active employees")
            
            # Exclude the user who created the announcement if provided
            if exclude_user:
                employees = employees.exclude(id=exclude_user.id)
                logger.info(f"After excluding creator, {employees.count()} employees remain")
            
            title = f"📢 {announcement.title}"
            body = announcement.description[:100] + '...' if len(announcement.description) > 100 else announcement.description
            
            logger.info(f"Sending announcement notification to employees: title={title}")
            result = NotificationService.send_to_users(
                employees, title, body, 'info',
                {'type': 'announcement', 'announcement_id': str(announcement.id)}
            )
            logger.info(f"Announcement notification result: {result}")
            return result
        
        logger.info(f"Announcement not active, skipping notification")
        return {'success': False, 'message': 'Announcement not active'}
    
    @staticmethod
    def notify_leave_request_submitted(leave_application):
        """Notify admins when an employee submits a leave request"""
        user = leave_application.user
        title = "📋 New Leave Request"
        body = f"{user.first_name} {user.last_name} requested {leave_application.leave_type.name} leave from {leave_application.start_date} to {leave_application.end_date}"
        
        return NotificationService.send_to_admins(
            title, body, 'info',
            {'type': 'leave_request', 'leave_id': str(leave_application.id)}
        )
    
    @staticmethod
    def notify_leave_approved(leave_application):
        """Notify employee when their leave is approved"""
        title = "✅ Leave Approved"
        body = f"Your {leave_application.leave_type.name} leave from {leave_application.start_date} to {leave_application.end_date} has been approved"
        
        return NotificationService.send_to_user(
            leave_application.user, title, body, 'success',
            {'type': 'leave_approved', 'leave_id': str(leave_application.id)}
        )
    
    @staticmethod
    def notify_leave_rejected(leave_application, reason=None):
        """Notify employee when their leave is rejected"""
        title = "❌ Leave Rejected"
        body = f"Your {leave_application.leave_type.name} leave request has been rejected"
        if reason:
            body += f". Reason: {reason[:50]}"
        
        return NotificationService.send_to_user(
            leave_application.user, title, body, 'error',
            {'type': 'leave_rejected', 'leave_id': str(leave_application.id)}
        )
    
    @staticmethod
    def notify_profile_update_submitted(profile_request):
        """Notify admins when an employee submits a profile update request"""
        user = profile_request.user
        title = "👤 Profile Update Request"
        body = f"{user.first_name} {user.last_name} requested to update their {profile_request.field_name}"
        
        return NotificationService.send_to_admins(
            title, body, 'info',
            {'type': 'profile_update', 'request_id': str(profile_request.id)}
        )
    
    @staticmethod
    def notify_profile_update_approved(profile_request):
        """Notify employee when their profile update is approved"""
        title = "✅ Profile Update Approved"
        body = f"Your request to update {profile_request.field_name} has been approved"
        
        return NotificationService.send_to_user(
            profile_request.user, title, body, 'success',
            {'type': 'profile_approved', 'request_id': str(profile_request.id)}
        )
    
    @staticmethod
    def notify_profile_update_rejected(profile_request, reason=None):
        """Notify employee when their profile update is rejected"""
        title = "❌ Profile Update Rejected"
        body = f"Your request to update {profile_request.field_name} has been rejected"
        if reason:
            body += f". Reason: {reason[:50]}"
        
        return NotificationService.send_to_user(
            profile_request.user, title, body, 'error',
            {'type': 'profile_rejected', 'request_id': str(profile_request.id)}
        )
