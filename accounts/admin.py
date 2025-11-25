from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Organization, Role, Permission, Module
from .forms import CustomUserCreationForm, CustomUserChangeForm


class UserAdmin(BaseUserAdmin):
    # Use custom forms
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    # Fields to display in the admin list view
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'employee_type', 'is_active', 'probation_status', 'notice_status', 'folder_status')
    list_filter = ('is_active', 'is_staff', 'role', 'employee_type', 'joining_date', 'is_on_probation', 'is_on_notice_period')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    
    # Fields for the admin form
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'birth_date', 'gender', 'marital_status')
        }),
        ('Employment info', {
            'fields': ('organization', 'role', 'employee_type', 'joining_date', 'termination_date', 'salary')
        }),
        ('Employment Status', {
            'fields': ('is_on_probation', 'probation_months', 'is_on_notice_period', 'notice_period_end_date'),
            'classes': ('collapse',),
            'description': 'Manage probation and notice period status'
        }),
        ('Relationships', {
            'fields': ('designations', 'shifts', 'technologies'),
            'classes': ('collapse',)
        }),
        ('Contact info', {
            'fields': ('emergency_contact', 'emergency_phone', 'current_address', 'permanent_address'),
            'classes': ('collapse',)
        }),
        ('File Management', {
            'fields': ('profile_picture', 'folder_path', 'create_employee_folder'),
            'classes': ('collapse',),
            'description': 'Manage employee files and folder creation'
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Fields for adding a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
        ('Personal info', {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'phone')
        }),
        ('Employment info', {
            'classes': ('wide',),
            'fields': ('organization', 'role', 'employee_type', 'joining_date', 'salary')
        }),
        ('Employment Status', {
            'classes': ('wide',),
            'fields': ('is_on_probation', 'probation_months'),
            'description': 'Set probation status for new employees'
        }),
        ('File Management', {
            'classes': ('wide',),
            'fields': ('create_employee_folder',),
            'description': 'Check this to create a dedicated folder structure for this employee'
        }),
    )
    
    readonly_fields = ('folder_path', 'created_at', 'updated_at', 'last_login', 'date_joined')
    
    def probation_status(self, obj):
        """Display probation status"""
        if obj.is_on_probation:
            months = obj.probation_months or 'N/A'
            return format_html('<span style="color: orange;">On Probation ({} months)</span>', months)
        return format_html('<span style="color: green;">Regular</span>')
    probation_status.short_description = 'Probation Status'
    
    def notice_status(self, obj):
        """Display notice period status"""
        if obj.is_on_notice_period:
            end_date = obj.notice_period_end_date.strftime('%Y-%m-%d') if obj.notice_period_end_date else 'N/A'
            return format_html('<span style="color: red;">On Notice (ends: {})</span>', end_date)
        return format_html('<span style="color: green;">Active</span>')
    notice_status.short_description = 'Notice Status'
    
    def folder_status(self, obj):
        """Display folder creation status"""
        if obj.folder_path:
            return format_html('<span style="color: green;">✓ Created</span>')
        return format_html('<span style="color: gray;">Not created</span>')
    folder_status.short_description = 'Folder Status'
    
    def create_employee_folder(self, obj):
        """Custom field for folder creation checkbox"""
        return False
    create_employee_folder.boolean = True
    create_employee_folder.short_description = 'Create Employee Folder'
    
    def save_model(self, request, obj, form, change):
        """Override save to handle folder creation"""
        # Check if this is a new object or if folder creation was requested
        create_folder = getattr(form, 'create_folder_requested', False)
        
        # Save the object first
        super().save_model(request, obj, form, change)
        
        # Handle folder creation if requested and not already created
        if create_folder and not obj.folder_path:
            self._create_employee_folder(obj)
    
    def _create_employee_folder(self, instance):
        """Create folder structure for employee"""
        import os
        from django.conf import settings
        
        folder_name = f"{instance.first_name}_{instance.last_name}_{instance.id}"
        folder_path = os.path.join('employee_folders', folder_name)
        full_folder_path = os.path.join(settings.MEDIA_ROOT, folder_path)
        
        try:
            # Create main employee folder
            os.makedirs(full_folder_path, exist_ok=True)
            
            # Create subfolders for organization
            subfolders = ['documents', 'images', 'contracts', 'certificates']
            for subfolder in subfolders:
                subfolder_path = os.path.join(full_folder_path, subfolder)
                os.makedirs(subfolder_path, exist_ok=True)
            
            instance.folder_path = folder_path
            instance.save(update_fields=['folder_path'])
            
            self.message_user(
                None, 
                f"Successfully created folder structure for {instance.username} at {folder_path}",
                level='SUCCESS'
            )
        except Exception as e:
            self.message_user(
                None,
                f"Failed to create folder for {instance.username}: {e}",
                level='ERROR'
            )


class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'industry', 'is_active', 'created_at')
    list_filter = ('is_active', 'industry')
    search_fields = ('name', 'short_name')


class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'display_name')
    filter_horizontal = ('permissions',)


class PermissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'codename', 'module', 'is_active')
    list_filter = ('is_active', 'module')
    search_fields = ('name', 'codename')


class ModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'display_name')


# Register models with admin
admin.site.register(User, UserAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(Permission, PermissionAdmin)
admin.site.register(Module, ModuleAdmin)
