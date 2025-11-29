from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, Organization, Module, Permission, Role, ProfileUpdateRequest


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'industry', 'is_active', 'created_at']
    list_filter = ['is_active', 'industry', 'created_at']
    search_fields = ['name', 'short_name', 'industry']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Organization Details', {
            'fields': ('name', 'short_name', 'industry', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'display_name']
    readonly_fields = ['created_at']


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['codename', 'name', 'module', 'is_active', 'created_at']
    list_filter = ['is_active', 'module', 'created_at']
    search_fields = ['codename', 'name', 'module__name']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('module')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'permissions_count', 'can_check_in_on_audit', 'is_active', 'created_at']
    list_filter = ['is_active', 'can_check_in_on_audit', 'created_at']
    search_fields = ['name', 'display_name']
    filter_horizontal = ['permissions']
    readonly_fields = ['created_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'display_name', 'is_active')
        }),
        ('Permissions', {
            'fields': ('permissions',)
        }),
        ('Audit Access', {
            'fields': ('can_check_in_on_audit',),
            'description': 'Enable "Check In On Audit" button for employees with this role. This allows check-in anytime without time restrictions.'
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def permissions_count(self, obj):
        count = obj.permissions.count()
        return format_html(
            '<span style="color: blue; font-weight: bold;">{}</span>',
            count
        )
    permissions_count.short_description = 'Permissions'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'employee_id', 'username', 'first_name', 'last_name', 'email',
        'organization', 'role', 'employee_type', 'is_active', 'joining_date'
    ]
    list_filter = [
        'is_active', 'is_staff', 'is_superuser', 'organization', 'role',
        'employee_type', 'joining_date', 'is_on_probation', 'is_on_notice_period','contract_start_date','contract_end_date'
    ]
    search_fields = [
        'employee_id', 'username', 'first_name', 'last_name', 'email', 'phone'
    ]
    readonly_fields = [
        'employee_id', 'date_joined', 'last_login', 'created_at', 'updated_at'
    ]
    filter_horizontal = ['shifts', 'designations', 'technologies', 'groups', 'user_permissions']
    
    fieldsets = (
        ('Authentication', {
            'fields': ('employee_id', 'username', 'password', 'plain_password')
        }),
        ('Personal Information', {
            'fields': (
                'first_name', 'last_name', 'email', 'phone', 'profile_picture',
                'birth_date', 'gender', 'marital_status'
            )
        }),
        ('Employment Details', {
            'fields': (
                'organization', 'role', 'employee_type', 'joining_date',
                'termination_date', 'salary', 'designations', 'technologies', 'shifts'
            )
        }),
        ('Contract Details', { 
            'fields': (
                'contract_start_date', 'contract_end_date'
            ),
        }),
        ('Status & Probation', {
            'fields': (
                'is_on_probation', 'probation_months', 'is_on_notice_period',
                'notice_period_end_date'
            )
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact', 'emergency_phone'),
            'classes': ('collapse',)
        }),
        ('Address Information', {
            'fields': ('current_address', 'permanent_address'),
            'classes': ('collapse',)
        }),
        ('File Management', {
            'fields': ('folder_path', 'employee_folder'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('employee_details',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('date_joined', 'last_login', 'created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Required Information', {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'email', 'password1', 'password2'),
        }),
        ('Employment Details', {
            'classes': ('wide',),
            'fields': ('organization', 'role', 'employee_type', 'joining_date'),
        }),
        ('Contract Details', { 
            'classes': ('wide',),
            'fields': ('contract_start_date', 'contract_end_date'),
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'organization', 'role', 'employee_type', 'current_address', 'permanent_address'
        ).prefetch_related('designations', 'technologies', 'shifts')


@admin.register(ProfileUpdateRequest)
class ProfileUpdateRequestAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'field_name', 'status', 'requested_at', 'processed_at', 'approved_by'
    ]
    list_filter = ['status', 'requested_at', 'processed_at', 'field_name']
    search_fields = ['user__username', 'user__email', 'field_name', 'reason']
    readonly_fields = ['requested_at', 'processed_at']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('user', 'field_name', 'old_value', 'new_value', 'reason')
        }),
        ('Status & Approval', {
            'fields': ('status', 'admin_comment', 'approved_by')
        }),
        ('Timestamps', {
            'fields': ('requested_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'approved_by')