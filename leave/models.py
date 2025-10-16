from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from accounts.models import User, Role
from datetime import date, timedelta
from decimal import Decimal


class LeaveType(models.Model):
    """Different types of leave (Annual, Sick, Maternity, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    is_paid = models.BooleanField(default=True)
    description = models.TextField(null=True, blank=True)
    color_code = models.CharField(max_length=7, default='#007bff', help_text="Hex color code for UI display")
    icon = models.CharField(max_length=50, null=True, blank=True, help_text="Icon class for UI display")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['code', 'is_active'])]
        ordering = ['name']

    def __str__(self):
        return self.name


class LeaveTypePolicy(models.Model):
    """Leave-type specific policies with flexible rules"""
    FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    GENDER_CHOICES = [
        ('all', 'All Genders'),
        ('male', 'Male Only'),
        ('female', 'Female Only'),
    ]
    
    name = models.CharField(max_length=100)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='policies')
    applicable_roles = models.ManyToManyField(Role, blank=True)
    applicable_gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='all')
    
    # Allocation and accrual
    annual_quota = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Annual leave quota")
    accrual_frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='monthly')
    accrual_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Leave accrued per frequency period")
    
    # Usage limits
    max_per_week = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum days per week")
    max_per_month = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum days per month")
    max_per_year = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum days per year")
    max_consecutive_days = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum consecutive days")
    
    # Notice and approval requirements
    min_notice_days = models.PositiveIntegerField(default=0, help_text="Minimum notice required in days")
    requires_approval = models.BooleanField(default=True)
    auto_approve_threshold = models.PositiveIntegerField(null=True, blank=True, help_text="Auto-approve if less than or equal to this many days")
    
    # Carry forward and expiry
    carry_forward_enabled = models.BooleanField(default=False)
    carry_forward_limit = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Maximum days that can be carried forward")
    carry_forward_expiry_months = models.PositiveIntegerField(default=12, help_text="Months after which carried forward leave expires")
    
    # Probation and tenure requirements
    min_tenure_days = models.PositiveIntegerField(default=0, help_text="Minimum days of employment required")
    available_during_probation = models.BooleanField(default=True)
    
    # Weekend and holiday settings
    include_weekends = models.BooleanField(default=False, help_text="Whether weekends count as leave days")
    include_holidays = models.BooleanField(default=False, help_text="Whether holidays count as leave days")
    
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(default=date.today)
    effective_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['leave_type', 'is_active']),
            models.Index(fields=['effective_from', 'effective_to']),
        ]
        unique_together = ('name', 'leave_type')
        ordering = ['leave_type__name', 'name']

    def __str__(self):
        return f"{self.leave_type.name} - {self.name}"
    
    def is_applicable_for_user(self, user):
        """Check if this policy applies to the given user"""
        # Check role
        if self.applicable_roles.exists() and user.role not in self.applicable_roles.all():
            return False
        
        # Check gender
        if self.applicable_gender != 'all' and user.gender != self.applicable_gender:
            return False
        
        # Check tenure
        if user.joining_date and self.min_tenure_days > 0:
            tenure_days = (date.today() - user.joining_date).days
            if tenure_days < self.min_tenure_days:
                return False
        
        # Check probation
        if user.is_on_probation and not self.available_during_probation:
            return False
        
        # Check effective dates
        today = date.today()
        if self.effective_from > today:
            return False
        if self.effective_to and self.effective_to < today:
            return False
        
        return True


class LeaveBalance(models.Model):
    """User's leave balance for each leave type"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    policy = models.ForeignKey(LeaveTypePolicy, on_delete=models.SET_NULL, null=True, blank=True)
    year = models.PositiveIntegerField()
    
    # Balance tracking
    opening_balance = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    accrued_balance = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    used_balance = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    carried_forward = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    adjustment = models.DecimalField(max_digits=7, decimal_places=2, default=0, help_text="Manual adjustments by admin")
    
    # Usage tracking for limits
    used_this_week = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    used_this_month = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    last_accrual_date = models.DateField(null=True, blank=True)
    last_reset_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'leave_type', 'year')
        indexes = [
            models.Index(fields=['user', 'year']),
            models.Index(fields=['leave_type', 'year']),
        ]
        ordering = ['user__username', 'leave_type__name', '-year']

    def __str__(self):
        return f"{self.user.username} - {self.leave_type.name} ({self.year})"
    
    @property
    def total_available(self):
        """Total available leave balance"""
        return self.opening_balance + self.accrued_balance + self.carried_forward + self.adjustment
    
    @property
    def remaining_balance(self):
        """Remaining leave balance"""
        return self.total_available - self.used_balance
    
    @property
    def pending_balance(self):
        """Balance including pending applications"""
        pending_days = self.user.leave_applications.filter(
            leave_type=self.leave_type,
            status='pending',
            start_date__year=self.year
        ).aggregate(
            total=models.Sum('total_days')
        )['total'] or 0
        return self.remaining_balance - pending_days
    
    def can_apply_for_days(self, days, start_date=None, end_date=None):
        """Check if user can apply for specified number of days"""
        if days <= 0:
            return False, "Invalid number of days"
        
        if self.remaining_balance < days:
            return False, f"Insufficient balance. Available: {self.remaining_balance}, Requested: {days}"
        
        # Check leave type specific policy restrictions
        if self.policy:
            # Check weekly limit
            if self.policy.max_per_week and start_date:
                week_start = start_date - timedelta(days=start_date.weekday())
                week_end = week_start + timedelta(days=6)
                week_used = self.user.leave_applications.filter(
                    leave_type=self.leave_type,
                    status__in=['approved', 'pending'],
                    start_date__gte=week_start,
                    end_date__lte=week_end
                ).aggregate(total=models.Sum('total_days'))['total'] or 0
                
                if week_used + days > self.policy.max_per_week:
                    return False, f"Weekly limit exceeded. Limit: {self.policy.max_per_week}, Used: {week_used}, Requested: {days}"
            
            # Check monthly limit
            if self.policy.max_per_month and start_date:
                month_used = self.user.leave_applications.filter(
                    leave_type=self.leave_type,
                    status__in=['approved', 'pending'],
                    start_date__year=start_date.year,
                    start_date__month=start_date.month
                ).aggregate(total=models.Sum('total_days'))['total'] or 0
                
                if month_used + days > self.policy.max_per_month:
                    return False, f"Monthly limit exceeded. Limit: {self.policy.max_per_month}, Used: {month_used}, Requested: {days}"
        
        # Check overall leave policy restrictions
        overall_policies = OverallLeavePolicy.objects.filter(is_active=True)
        for overall_policy in overall_policies:
            if not overall_policy.is_applicable_for_user(self.user):
                continue
            
            # Check overall weekly limit
            if overall_policy.max_total_per_week and start_date:
                week_start = start_date - timedelta(days=start_date.weekday())
                week_end = week_start + timedelta(days=6)
                total_week_used = self.user.leave_applications.filter(
                    status__in=['approved', 'pending'],
                    start_date__gte=week_start,
                    end_date__lte=week_end
                ).aggregate(total=models.Sum('total_days'))['total'] or 0
                
                if total_week_used + days > overall_policy.max_total_per_week:
                    return False, f"Overall weekly limit exceeded. Limit: {overall_policy.max_total_per_week}, Used: {total_week_used}, Requested: {days}"
            
            # Check overall monthly limit
            if overall_policy.max_total_per_month and start_date:
                total_month_used = self.user.leave_applications.filter(
                    status__in=['approved', 'pending'],
                    start_date__year=start_date.year,
                    start_date__month=start_date.month
                ).aggregate(total=models.Sum('total_days'))['total'] or 0
                
                if total_month_used + days > overall_policy.max_total_per_month:
                    return False, f"Overall monthly limit exceeded. Limit: {overall_policy.max_total_per_month}, Used: {total_month_used}, Requested: {days}"
            
            # Check advance booking limits
            if start_date:
                days_in_advance = (start_date - date.today()).days
                if overall_policy.max_advance_booking_days and days_in_advance > overall_policy.max_advance_booking_days:
                    return False, f"Cannot book leave more than {overall_policy.max_advance_booking_days} days in advance"
                if days_in_advance < overall_policy.min_advance_booking_days:
                    return False, f"Leave must be booked at least {overall_policy.min_advance_booking_days} days in advance"
        
        # Check blackout dates
        if start_date and end_date:
            blackout_dates = LeaveBlackoutDate.objects.filter(
                is_active=True,
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            for blackout in blackout_dates:
                if blackout.is_applicable_for_user_and_leave_type(self.user, self.leave_type):
                    return False, f"Leave not allowed during blackout period: {blackout.name} ({blackout.reason})"
        
        return True, "Application allowed"
    
    def get_accrual_amount_for_period(self, period_start, period_end):
        """Calculate accrual amount for a given period based on policy"""
        if not self.policy or self.policy.accrual_rate <= 0:
            return Decimal('0')
        
        if self.policy.accrual_frequency == 'monthly':
            # Calculate number of complete months in the period
            months = 0
            current_date = period_start.replace(day=1)
            while current_date <= period_end:
                if current_date >= period_start:
                    months += 1
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
            return self.policy.accrual_rate * months
        
        elif self.policy.accrual_frequency == 'weekly':
            # Calculate number of complete weeks
            days_in_period = (period_end - period_start).days + 1
            weeks = days_in_period // 7
            return self.policy.accrual_rate * weeks
        
        elif self.policy.accrual_frequency == 'yearly':
            # Check if the period spans a full year
            if (period_end - period_start).days >= 364:  # Allow for leap years
                return self.policy.accrual_rate
            return Decimal('0')
        
        return Decimal('0')


class LeaveApplication(models.Model):
    """Leave application submitted by employees"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    # Basic information
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_applications')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    policy = models.ForeignKey(LeaveTypePolicy, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Leave details
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.DecimalField(max_digits=5, decimal_places=2)
    is_half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(max_length=10, choices=[('morning', 'Morning'), ('afternoon', 'Afternoon')], null=True, blank=True)
    
    # Application details
    reason = models.TextField()
    emergency_contact = models.CharField(max_length=100, null=True, blank=True)
    emergency_phone = models.CharField(max_length=15, null=True, blank=True)
    work_handover = models.TextField(null=True, blank=True, help_text="Work handover details")
    
    # Status and approval
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    admin_comments = models.TextField(null=True, blank=True)
    
    # Tracking
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # File attachments (for medical certificates, etc.)
    attachment = models.FileField(upload_to='leave_attachments/', null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['leave_type', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['applied_at']),
        ]
        ordering = ['-applied_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.leave_type.name} ({self.start_date} to {self.end_date})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError("Start date cannot be after end date")
            
            # Calculate total days
            if self.is_half_day and self.start_date == self.end_date:
                self.total_days = Decimal('0.5')
            else:
                days = (self.end_date - self.start_date).days + 1
                if self.policy and not self.policy.include_weekends:
                    # Calculate working days only
                    working_days = 0
                    current_date = self.start_date
                    while current_date <= self.end_date:
                        if current_date.weekday() < 5:  # Monday = 0, Sunday = 6
                            working_days += 1
                        current_date += timedelta(days=1)
                    days = working_days
                self.total_days = Decimal(str(days))
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def can_be_cancelled(self):
        """Check if application can be cancelled by user"""
        return self.status in ['draft', 'pending'] and self.start_date >= date.today()
    
    def can_be_edited(self):
        """Check if application can be edited by user"""
        return self.status == 'draft' or (self.status == 'pending' and self.start_date > date.today())
    
    def can_be_deleted_by_user(self):
        """Check if application can be deleted by the user (until start date)"""
        return self.status in ['draft', 'pending'] and self.start_date > date.today()
    
    def can_be_deleted_by_admin(self):
        """Check if application can be deleted by admin"""
        # Admin can delete any application except:
        # 1. Approved applications that have already ended (to maintain records)
        # 2. Cancelled applications (user already cancelled, should preserve)
        
        # Allow deletion of rejected applications (admin can clean up)
        if self.status == 'rejected':
            return True
            
        # Block cancelled applications (user action, preserve record)
        if self.status == 'cancelled':
            return False
            
        # For pending/approved applications, allow deletion until end date
        return self.end_date >= date.today()
    
    def approve(self, approved_by, comments=None):
        """Approve the leave application"""
        self.status = 'approved'
        self.approved_by = approved_by
        self.approved_at = timezone.now()
        if comments:
            self.admin_comments = comments
        self.save()
        
        # Update leave balance - deduct the approved days
        balance, created = LeaveBalance.objects.get_or_create(
            user=self.user,
            leave_type=self.leave_type,
            year=self.start_date.year,
            defaults={'policy': self.policy}
        )
        balance.used_balance += self.total_days
        balance.save()
    
    def reject(self, rejected_by, reason, comments=None):
        """Reject the leave application"""
        # If this was previously approved, restore the balance
        if self.status == 'approved':
            try:
                balance = LeaveBalance.objects.get(
                    user=self.user,
                    leave_type=self.leave_type,
                    year=self.start_date.year
                )
                balance.used_balance = max(Decimal('0'), balance.used_balance - self.total_days)
                balance.save()
            except LeaveBalance.DoesNotExist:
                pass
        
        self.status = 'rejected'
        self.approved_by = rejected_by
        self.rejection_reason = reason
        if comments:
            self.admin_comments = comments
        self.save()


class LeaveApplicationComment(models.Model):
    """Comments/discussions on leave applications"""
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    is_internal = models.BooleanField(default=False, help_text="Internal admin comment not visible to employee")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.application}"


class LeaveCalendar(models.Model):
    """Calendar view of approved leaves for better planning"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    date = models.DateField()
    is_half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(max_length=10, choices=[('morning', 'Morning'), ('afternoon', 'Afternoon')], null=True, blank=True)
    
    class Meta:
        unique_together = ('user', 'date')
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['user', 'date']),
        ]
        ordering = ['date']
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"


class OverallLeavePolicy(models.Model):
    """Overall leave restrictions that apply across all leave types"""
    name = models.CharField(max_length=100, unique=True)
    applicable_roles = models.ManyToManyField(Role, blank=True)
    
    # Total leave limits (across all leave types)
    max_total_per_week = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum total leaves per week")
    max_total_per_month = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum total leaves per month")
    max_total_per_year = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum total leaves per year")
    
    # Consecutive leave restrictions
    max_total_consecutive_days = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum consecutive days across all leave types")
    min_gap_between_leaves = models.PositiveIntegerField(default=0, help_text="Minimum gap required between leave applications (in days)")
    
    # Advance booking restrictions
    max_advance_booking_days = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum days in advance for booking leave")
    min_advance_booking_days = models.PositiveIntegerField(default=0, help_text="Minimum days in advance for booking leave")
    
    # Simultaneous leave restrictions
    max_simultaneous_leaves_in_team = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum people on leave simultaneously in a team")
    max_simultaneous_leaves_in_department = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum people on leave simultaneously in a department")
    
    # Emergency leave settings
    allow_emergency_leave = models.BooleanField(default=True)
    emergency_leave_max_days = models.PositiveIntegerField(default=3, help_text="Maximum emergency leave days without prior approval")
    
    # Weekend and holiday considerations
    block_leave_before_weekend = models.BooleanField(default=False)
    block_leave_after_weekend = models.BooleanField(default=False)
    block_leave_before_holiday = models.BooleanField(default=False)
    block_leave_after_holiday = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(default=date.today)
    effective_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['is_active', 'effective_from']),
        ]
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def is_applicable_for_user(self, user):
        """Check if this policy applies to the given user"""
        # Check role
        if self.applicable_roles.exists() and user.role not in self.applicable_roles.all():
            return False
        
        # Check effective dates
        today = date.today()
        if self.effective_from > today:
            return False
        if self.effective_to and self.effective_to < today:
            return False
        
        return True


class LeaveBlackoutDate(models.Model):
    """Dates when leaves are not allowed (company-wide or for specific roles)"""
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    applicable_roles = models.ManyToManyField(Role, blank=True)
    applicable_leave_types = models.ManyToManyField(LeaveType, blank=True)
    reason = models.TextField(help_text="Reason for blackout period")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
        ]
        ordering = ['start_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"
    
    def is_applicable_for_user_and_leave_type(self, user, leave_type):
        """Check if blackout applies to user and leave type"""
        if not self.is_active:
            return False
        
        # Check role
        if self.applicable_roles.exists() and user.role not in self.applicable_roles.all():
            return False
        
        # Check leave type
        if self.applicable_leave_types.exists() and leave_type not in self.applicable_leave_types.all():
            return False
        
        return True


class LeaveBalanceAudit(models.Model):
    """Audit trail for leave balance changes"""
    ACTION_CHOICES = [
        ('annual_reset', 'Annual Reset'),
        ('manual_adjustment', 'Manual Adjustment'),
        ('accrual', 'Monthly/Weekly Accrual'),
        ('usage', 'Leave Usage'),
        ('carry_forward', 'Carry Forward'),
        ('policy_change', 'Policy Change'),
        ('correction', 'Balance Correction'),
    ]
    
    balance = models.ForeignKey(LeaveBalance, on_delete=models.CASCADE, related_name='audit_trail')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    old_balance = models.DecimalField(max_digits=7, decimal_places=2)
    new_balance = models.DecimalField(max_digits=7, decimal_places=2)
    change_amount = models.DecimalField(max_digits=7, decimal_places=2)
    reason = models.TextField()
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reference_id = models.CharField(max_length=100, null=True, blank=True, help_text="Reference to related object (e.g., leave application ID)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['balance', 'action']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.balance} - {self.action} ({self.change_amount})"


class FlexibleTimingType(models.Model):
    """Types of flexible timing requests (late arrival, early departure, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(null=True, blank=True)
    max_duration_minutes = models.PositiveIntegerField(default=60, help_text="Maximum duration in minutes")
    max_per_month = models.PositiveIntegerField(default=2, help_text="Maximum requests per month")
    requires_approval = models.BooleanField(default=True)
    advance_notice_hours = models.PositiveIntegerField(default=2, help_text="Minimum advance notice required in hours")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class FlexibleTimingRequest(models.Model):
    """Flexible timing requests (late arrival, early departure)"""
    TIMING_CHOICES = [
        ('late_arrival', 'Late Arrival'),
        ('early_departure', 'Early Departure'),
        ('extended_break', 'Extended Break'),
        ('custom', 'Custom Timing'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('used', 'Used'),
        ('expired', 'Expired'),
    ]

    # Basic information
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flexible_timing_requests')
    timing_type = models.ForeignKey(FlexibleTimingType, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=20, choices=TIMING_CHOICES, default='late_arrival')
    
    # Timing details
    requested_date = models.DateField()
    duration_minutes = models.PositiveIntegerField(help_text="Duration in minutes")
    start_time = models.TimeField(null=True, blank=True, help_text="For custom timing requests")
    end_time = models.TimeField(null=True, blank=True, help_text="For custom timing requests")
    
    # Request details
    reason = models.TextField()
    is_emergency = models.BooleanField(default=False)
    
    # Status and approval
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_timing_requests')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    admin_comments = models.TextField(null=True, blank=True)
    
    # Usage tracking
    used_at = models.DateTimeField(null=True, blank=True, help_text="When the flexible timing was actually used")
    actual_duration_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Actual duration used")
    
    # Tracking
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['requested_date', 'status']),
            models.Index(fields=['timing_type', 'status']),
            models.Index(fields=['applied_at']),
        ]
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.user.username} - {self.get_request_type_display()} ({self.requested_date})"

    def clean(self):
        from django.core.exceptions import ValidationError
        from datetime import datetime, timedelta
        
        # Validate duration doesn't exceed type limit
        if self.timing_type and self.duration_minutes > self.timing_type.max_duration_minutes:
            raise ValidationError(f"Duration cannot exceed {self.timing_type.max_duration_minutes} minutes for {self.timing_type.name}")
        
        # Validate advance notice
        if self.timing_type and self.requested_date and not self.is_emergency:
            notice_required = timedelta(hours=self.timing_type.advance_notice_hours)
            request_datetime = datetime.combine(self.requested_date, datetime.min.time())
            if datetime.now() + notice_required > request_datetime:
                raise ValidationError(f"Minimum {self.timing_type.advance_notice_hours} hours advance notice required")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def can_be_cancelled(self):
        """Check if request can be cancelled by user"""
        return self.status in ['draft', 'pending', 'approved'] and self.requested_date >= date.today()

    def can_be_used(self):
        """Check if approved request can be used"""
        return (self.status == 'approved' and 
                self.requested_date == date.today() and 
                not self.used_at)

    def mark_as_used(self, actual_duration=None):
        """Mark the request as used"""
        self.status = 'used'
        self.used_at = timezone.now()
        if actual_duration:
            self.actual_duration_minutes = actual_duration
        self.save()

    def get_monthly_usage_count(self):
        """Get count of approved/used requests for the same month"""
        return FlexibleTimingRequest.objects.filter(
            user=self.user,
            timing_type=self.timing_type,
            requested_date__year=self.requested_date.year,
            requested_date__month=self.requested_date.month,
            status__in=['approved', 'used']
        ).exclude(id=self.id).count()

    def validate_monthly_limit(self):
        """Check if monthly limit is exceeded"""
        current_count = self.get_monthly_usage_count()
        return current_count < self.timing_type.max_per_month


class FlexibleTimingBalance(models.Model):
    """Track user's flexible timing balance and usage"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flexible_timing_balances')
    timing_type = models.ForeignKey(FlexibleTimingType, on_delete=models.CASCADE)
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()
    
    # Usage tracking
    total_allowed = models.PositiveIntegerField(default=0)
    used_count = models.PositiveIntegerField(default=0)
    pending_count = models.PositiveIntegerField(default=0)
    
    # Duration tracking (in minutes)
    total_duration_used = models.PositiveIntegerField(default=0)
    total_duration_pending = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'timing_type', 'year', 'month')
        indexes = [
            models.Index(fields=['user', 'year', 'month']),
            models.Index(fields=['timing_type', 'year', 'month']),
        ]
        ordering = ['user__username', 'timing_type__name', '-year', '-month']

    def __str__(self):
        return f"{self.user.username} - {self.timing_type.name} ({self.year}-{self.month:02d})"

    @property
    def remaining_count(self):
        """Remaining requests available"""
        return max(0, self.total_allowed - self.used_count - self.pending_count)

    @property
    def can_request_more(self):
        """Check if user can make more requests"""
        return self.remaining_count > 0

    def update_usage(self):
        """Update usage counts based on actual requests"""
        requests = FlexibleTimingRequest.objects.filter(
            user=self.user,
            timing_type=self.timing_type,
            requested_date__year=self.year,
            requested_date__month=self.month
        )
        
        self.used_count = requests.filter(status='used').count()
        self.pending_count = requests.filter(status__in=['pending', 'approved']).count()
        
        self.total_duration_used = sum(
            req.actual_duration_minutes or req.duration_minutes 
            for req in requests.filter(status='used')
        )
        self.total_duration_pending = sum(
            req.duration_minutes 
            for req in requests.filter(status__in=['pending', 'approved'])
        )
        
        self.save()


class FlexibleTimingPolicy(models.Model):
    """Policies for flexible timing management"""
    name = models.CharField(max_length=100, unique=True)
    applicable_roles = models.ManyToManyField(Role, blank=True)
    
    # General settings
    is_active = models.BooleanField(default=True)
    requires_manager_approval = models.BooleanField(default=True)
    requires_hr_approval = models.BooleanField(default=False)
    
    # Emergency settings
    allow_emergency_requests = models.BooleanField(default=True)
    emergency_auto_approve = models.BooleanField(default=False)
    emergency_max_duration = models.PositiveIntegerField(default=30, help_text="Max emergency duration in minutes")
    
    # Notification settings
    notify_manager = models.BooleanField(default=True)
    notify_hr = models.BooleanField(default=False)
    notify_team = models.BooleanField(default=False)
    
    # Restrictions
    blackout_dates = models.ManyToManyField('LeaveBlackoutDate', blank=True)
    min_team_strength_required = models.PositiveIntegerField(null=True, blank=True, help_text="Minimum team members required to be present")
    
    effective_from = models.DateField(default=date.today)
    effective_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def is_applicable_for_user(self, user):
        """Check if this policy applies to the given user"""
        if not self.is_active:
            return False
            
        # Check role
        if self.applicable_roles.exists() and user.role not in self.applicable_roles.all():
            return False
        
        # Check effective dates
        today = date.today()
        if self.effective_from > today:
            return False
        if self.effective_to and self.effective_to < today:
            return False
        
        return True
