from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
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

