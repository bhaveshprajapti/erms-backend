from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from accounts.models import User, Organization
from common.models import StatusChoice
from policies.models import LeaveType, FlexAllowanceType

class Attendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    sessions = models.JSONField(default=dict)
    total_hours = models.DurationField(null=True, blank=True)
    total_break_time = models.DurationField(null=True, blank=True)
    break_start_time = models.DateTimeField(null=True, blank=True)
    day_ended = models.BooleanField(default=False)
    day_end_time = models.DateTimeField(null=True, blank=True)
    day_status = models.CharField(max_length=20, null=True, blank=True)
    location = models.JSONField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    admin_reset_at = models.DateTimeField(null=True, blank=True)  # Track when admin reset the day
    admin_reset_count = models.PositiveIntegerField(default=0)  # Track number of resets per day
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date')
        indexes = [models.Index(fields=['user', 'date'])]

    def __str__(self):
        return f"{self.user.username} - {self.date}"


class LeaveRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.DecimalField(max_digits=5, decimal_places=2)
    half_day_type = models.CharField(max_length=20, null=True, blank=True)
    reason = models.TextField()
    document = models.FileField(upload_to='leave_documents/', null=True, blank=True)
    status = models.ForeignKey(StatusChoice, on_delete=models.SET_NULL, null=True, limit_choices_to={'category': 'leave_status'})
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leave_requests')
    rejection_reason = models.TextField(null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'start_date', 'status'])]

    def __str__(self):
        return f"{self.user.username} - {self.start_date} to {self.end_date}"


class TimeAdjustment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    attendance = models.ForeignKey(Attendance, on_delete=models.SET_NULL, null=True, blank=True)
    flex_type = models.ForeignKey(FlexAllowanceType, on_delete=models.CASCADE)
    date = models.DateField()
    duration_minutes = models.PositiveIntegerField()
    description = models.TextField(null=True, blank=True)
    status = models.ForeignKey(StatusChoice, on_delete=models.SET_NULL, null=True, limit_choices_to={'category': 'adjustment_status'})
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_time_adjustments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'date'])]

    def __str__(self):
        return f"{self.user.username} - {self.date}"


class Approval(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    request = GenericForeignKey('content_type', 'object_id')
    approver = models.ForeignKey(User, on_delete=models.CASCADE)
    level = models.PositiveIntegerField(default=1)
    status = models.ForeignKey(StatusChoice, on_delete=models.SET_NULL, null=True, limit_choices_to={'category': 'approval_status'})
    comments = models.TextField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    is_escalated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['content_type', 'object_id', 'level'])]

    def __str__(self):
        return f"Approval for {self.request} by {self.approver.username}"


class SessionLog(models.Model):
    """
    Audit trail for all attendance-related events and session management.
    This model tracks all user actions for security and compliance.
    """
    EVENT_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('check_in', 'Check In'),
        ('check_out', 'Check Out'),
        ('start_break', 'Start Break'),
        ('end_break', 'End Break'),
        ('end_of_day', 'End of Day'),
        ('auto_end_day', 'Auto End Day (Session Timeout)'),
        ('admin_reset', 'Admin Reset Day'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    date = models.DateField()  # The date this event relates to
    session_count = models.PositiveIntegerField(null=True, blank=True)
    location = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    # Session timeout tracking
    last_activity = models.DateTimeField(null=True, blank=True)
    is_session_active = models.BooleanField(default=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'date', 'event_type']),
            models.Index(fields=['user', 'is_session_active']),
            models.Index(fields=['last_activity']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} - {self.event_type} - {self.timestamp}"
    
    def is_session_expired(self):
        """Check if session has expired (1 hour 15 minutes of inactivity)"""
        if not self.last_activity or not self.is_session_active:
            return True
        
        timeout_duration = timezone.timedelta(hours=1, minutes=15)
        return timezone.now() - self.last_activity > timeout_duration
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
    
    @classmethod
    def log_event(cls, user, event_type, date=None, session_count=None, location=None, request=None, notes=None):
        """Helper method to log events with optional request context"""
        if date is None:
            # Use IST date for business logic
            from common.timezone_utils import get_current_ist_date
            date = get_current_ist_date()
        
        # Extract request metadata if available
        ip_address = None
        user_agent = None
        if request:
            ip_address = cls._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Limit length
        
        # Create the log entry
        log_entry = cls.objects.create(
            user=user,
            event_type=event_type,
            date=date,
            session_count=session_count,
            location=location,
            ip_address=ip_address,
            user_agent=user_agent,
            notes=notes,
            last_activity=timezone.now()
        )
        
        # For login events, mark any previous sessions as inactive
        if event_type == 'login':
            cls.objects.filter(
                user=user,
                is_session_active=True
            ).exclude(id=log_entry.id).update(is_session_active=False)
        
        # For logout events, mark session as inactive
        elif event_type == 'logout':
            log_entry.is_session_active = False
            log_entry.save(update_fields=['is_session_active'])
        
        return log_entry
    
    @staticmethod
    def _get_client_ip(request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @classmethod
    def get_active_session(cls, user):
        """Get the current active session for a user"""
        return cls.objects.filter(
            user=user,
            is_session_active=True,
            event_type='login'
        ).first()
    
    @classmethod
    def check_and_handle_expired_sessions(cls):
        """Check for expired sessions and auto-end workdays"""
        from .models import Attendance
        
        # Find all active sessions that have expired
        timeout_duration = timezone.timedelta(hours=1, minutes=15)
        cutoff_time = timezone.now() - timeout_duration
        
        expired_sessions = cls.objects.filter(
            is_session_active=True,
            event_type='login',
            last_activity__lt=cutoff_time
        )
        
        for session in expired_sessions:
            try:
                # Check if user has an active attendance record for today
                # Use IST date for business logic
                from common.timezone_utils import get_current_ist_date
                today = get_current_ist_date()
                attendance = Attendance.objects.filter(
                    user=session.user,
                    date=today,
                    day_ended=False
                ).first()
                
                if attendance:
                    # Auto-end the workday
                    sessions = attendance.sessions or []
                    
                    # If currently checked in, check out first
                    if sessions and 'check_out' not in sessions[-1]:
                        sessions[-1]['check_out'] = session.last_activity.isoformat()
                        sessions[-1]['location_out'] = {'lat': 0, 'lng': 0, 'auto_checkout': True}
                    
                    # End the day
                    attendance.sessions = sessions
                    attendance.day_ended = True
                    attendance.day_end_time = session.last_activity
                    attendance.break_start_time = None  # Clear any active break
                    
                    # Calculate final totals
                    from .views import AttendanceViewSet
                    viewset = AttendanceViewSet()
                    attendance.total_hours = viewset._calculate_total_hours(sessions)
                    attendance.day_status = viewset._calculate_day_status(attendance.total_hours)
                    attendance.save()
                    
                    # Log the auto-end event
                    cls.log_event(
                        user=session.user,
                        event_type='auto_end_day',
                        date=today,
                        notes=f'Auto-ended due to session timeout. Last activity: {session.last_activity}'
                    )
                
                # Mark session as inactive
                session.is_session_active = False
                session.save(update_fields=['is_session_active'])
                
            except Exception as e:
                # Log error but continue processing other sessions
                print(f"Error handling expired session for user {session.user.username}: {e}")
                continue
        
        return expired_sessions.count()

