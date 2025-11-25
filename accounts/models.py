from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Max
import re
from common.models import (
    Address, EmployeeType, Designation, Technology, Shift
)

class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    short_name = models.CharField(max_length=50, null=True, blank=True)
    industry = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name


class Module(models.Model):
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.display_name


class Permission(models.Model):
    codename = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['codename', 'module'])]

    def __str__(self):
        return self.name


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    permissions = models.ManyToManyField(Permission, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.display_name


class User(AbstractUser):
    employee_id = models.CharField(max_length=10, unique=True, null=True, blank=True, help_text="Auto-generated employee ID like DW0001")
    phone = models.CharField(max_length=15, null=True, blank=True)
    plain_password = models.CharField(max_length=128, blank=True, null=True, help_text="Plain text password for admin viewing")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    employee_type = models.ForeignKey(EmployeeType, on_delete=models.SET_NULL, null=True, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)
    contract_start_date = models.DateField(
        null=True, blank=True,
        help_text="Start date of the employee's contract (used for time-bound access)."
    )
    contract_end_date = models.DateField(
        null=True, blank=True,
        help_text="End date of the employee's contract (used for time-bound access)."
    )
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    marital_status = models.CharField(max_length=10, null=True, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    employee_details = models.JSONField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    folder_path = models.CharField(max_length=500, null=True, blank=True)
    employee_folder = models.ForeignKey('files.Folder', on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_ref')
    is_on_probation = models.BooleanField(default=False)
    probation_months = models.PositiveIntegerField(null=True, blank=True, help_text="Number of months for probation period")
    is_on_notice_period = models.BooleanField(default=False)
    notice_period_end_date = models.DateField(null=True, blank=True, help_text="End date of notice period")
    emergency_contact = models.CharField(max_length=100, null=True, blank=True)
    emergency_phone = models.CharField(max_length=15, null=True, blank=True)
    current_address = models.OneToOneField(Address, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_current_address')
    permanent_address = models.OneToOneField(Address, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_permanent_address')
    shifts = models.ManyToManyField(Shift, blank=True)
    designations = models.ManyToManyField(Designation, blank=True)
    technologies = models.ManyToManyField(Technology, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['employee_id', 'email', 'organization', 'joining_date'])]

    def generate_employee_id(self):
        """Generate auto-incremented employee ID starting with DW0001"""
        if self.employee_id:
            return self.employee_id
        
        # Get the highest existing employee_id number
        latest_user = User.objects.filter(
            employee_id__regex=r'^DW\d{4}$'
        ).aggregate(Max('employee_id'))['employee_id__max']
        
        if latest_user:
            # Extract number and increment
            number = int(latest_user[2:]) + 1
        else:
            # Start with 1 if no existing IDs
            number = 1
        
        return f"DW{number:04d}"
    
    def generate_username(self):
        """Generate username from first_name with DW prefix and unique suffix"""
        if not self.first_name:
            return self.username
        
        # Clean first name (remove special chars, make lowercase)
        base_username = re.sub(r'[^a-zA-Z]', '', self.first_name.lower())
        username_prefix = f"DW_{base_username}"
        
        # Check if base username exists
        existing_count = User.objects.filter(
            username__startswith=username_prefix
        ).count()
        
        if existing_count == 0:
            # If no similar username exists, try without suffix first
            if not User.objects.filter(username=username_prefix).exists():
                return username_prefix
        
        # Generate with 2-3 digit suffix
        counter = existing_count + 1
        while counter < 1000:  # Safety limit
            if counter < 100:
                suffix = f"{counter:02d}"
            else:
                suffix = f"{counter:03d}"
            
            new_username = f"{username_prefix}{suffix}"
            if not User.objects.filter(username=new_username).exists():
                return new_username
            counter += 1
        
        # Fallback to timestamp if all else fails
        import time
        return f"{username_prefix}{int(time.time()) % 1000}"
    
    def save(self, *args, **kwargs):
        # Generate employee_id if not set
        if not self.employee_id:
            self.employee_id = self.generate_employee_id()
        
        # Generate username if not set and first_name is available
        if not self.username and self.first_name:
            self.username = self.generate_username()
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.employee_id if self.employee_id else self.username


class EmployeePayment(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('fixed', 'Fixed Payment'),
        ('hourly', 'Hourly Payment'),
    ]
    
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employee_payments')
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Total amount for fixed payments")
    amount_per_hour = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Amount per hour for hourly payments")
    working_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Total working hours for hourly payments")
    date = models.DateField(help_text="Payment date")
    description = models.TextField(help_text="Payment description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['payment_type', 'date']),
        ]
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.employee.username} - {self.get_payment_type_display()} - ₹{self.amount}"


class ProfileUpdateRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile_update_requests')
    field_name = models.CharField(max_length=100, help_text="Name of the field being updated")
    old_value = models.TextField(null=True, blank=True, help_text="Previous value")
    new_value = models.TextField(help_text="New requested value")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(null=True, blank=True, help_text="Reason for update request")
    admin_comment = models.TextField(null=True, blank=True, help_text="Admin's comment on approval/rejection")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'requested_at']),
        ]
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.field_name} update ({self.status})"

