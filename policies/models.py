from django.db import models
from accounts.models import User, Role

class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    is_paid = models.BooleanField(default=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['code'])]

    def __str__(self):
        return self.name


class LeavePolicy(models.Model):
    name = models.CharField(max_length=100)
    leave_types = models.ManyToManyField(LeaveType)
    applicable_roles = models.ManyToManyField(Role, blank=True)
    annual_quota = models.PositiveIntegerField(default=0)
    monthly_accrual = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    carry_forward_limit = models.PositiveIntegerField(default=0)
    notice_days = models.PositiveIntegerField(default=0)
    max_consecutive = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name


class LeaveBalance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.PositiveIntegerField()
    opening_balance = models.DecimalField(max_digits=5, decimal_places=2)
    used = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    carried_forward = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    policy = models.ForeignKey(LeavePolicy, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def remaining(self):
        return self.opening_balance + self.carried_forward - self.used

    class Meta:
        unique_together = ('user', 'leave_type', 'year')
        indexes = [models.Index(fields=['user', 'year'])]

    def __str__(self):
        return f"{self.user.username} - {self.leave_type.name} ({self.year})"


class FlexAllowanceType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    duration_minutes = models.PositiveIntegerField()
    max_per_month = models.PositiveIntegerField()
    is_late = models.BooleanField(default=False)
    is_early = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['code'])]

    def __str__(self):
        return self.name


class FlexPolicy(models.Model):
    name = models.CharField(max_length=100)
    flex_types = models.ManyToManyField(FlexAllowanceType)
    applicable_roles = models.ManyToManyField(Role, blank=True)
    reset_monthly = models.BooleanField(default=True)
    carry_forward = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name


class FlexBalance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    flex_type = models.ForeignKey(FlexAllowanceType, on_delete=models.CASCADE)
    year_month = models.CharField(max_length=7)  # e.g., '2025-10'
    opening_count = models.PositiveIntegerField()
    used_count = models.PositiveIntegerField(default=0)
    policy = models.ForeignKey(FlexPolicy, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def remaining(self):
        return self.opening_count - self.used_count

    class Meta:
        unique_together = ('user', 'flex_type', 'year_month')
        indexes = [models.Index(fields=['user', 'year_month'])]

    def __str__(self):
        return f"{self.user.username} - {self.flex_type.name} ({self.year_month})"

