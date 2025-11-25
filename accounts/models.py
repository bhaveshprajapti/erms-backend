from django.contrib.auth.models import AbstractUser
from django.db import models
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
    description = models.TextField(null=True, blank=True)
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
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['codename', 'module'])]

    def __str__(self):
        return self.name


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.display_name


class User(AbstractUser):
    phone = models.CharField(max_length=15, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    employee_type = models.ForeignKey(EmployeeType, on_delete=models.SET_NULL, null=True, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    marital_status = models.CharField(max_length=10, null=True, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    employee_details = models.JSONField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    folder_path = models.CharField(max_length=500, null=True, blank=True)
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
        indexes = [models.Index(fields=['email', 'organization', 'joining_date'])]

    def __str__(self):
        return self.username


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

