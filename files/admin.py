from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Folder, File, FileShare


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'parent', 'folder_type', 'color_display', 'files_count',
        'subfolders_count', 'created_by', 'created_at'
    ]
    list_filter = [
        'color', 'is_project_folder', 'is_employee_folder', 'is_client_folder',
        'is_system_folder', 'created_at'
    ]
    search_fields = ['name', 'description', 'folder_link']
    readonly_fields = ['folder_link', 'files_count', 'subfolders_count', 'total_size', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Folder Information', {
            'fields': ('name', 'parent', 'description', 'color')
        }),
        ('Associations', {
            'fields': ('project', 'client', 'employee', 'created_by')
        }),
        ('Folder Type', {
            'fields': (
                'is_project_folder', 'is_employee_folder', 'is_client_folder', 'is_system_folder'
            )
        }),
        ('Statistics', {
            'fields': ('files_count', 'subfolders_count', 'total_size'),
            'classes': ('collapse',)
        }),
        ('Sharing', {
            'fields': ('folder_link',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def folder_type(self, obj):
        types = []
        if obj.is_project_folder:
            types.append('<span style="color: blue;">Project</span>')
        if obj.is_employee_folder:
            types.append('<span style="color: green;">Employee</span>')
        if obj.is_client_folder:
            types.append('<span style="color: orange;">Client</span>')
        if obj.is_system_folder:
            types.append('<span style="color: red;">System</span>')
        
        return format_html(' | '.join(types)) if types else '-'
    folder_type.short_description = 'Type'
    
    def color_display(self, obj):
        color_map = {
            'blue': '#007bff',
            'green': '#28a745',
            'yellow': '#ffc107',
            'red': '#dc3545',
            'purple': '#6f42c1',
            'orange': '#fd7e14',
            'pink': '#e83e8c',
            'gray': '#6c757d',
        }
        color_hex = color_map.get(obj.color, '#6c757d')
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; display: inline-block; border-radius: 3px;"></div>',
            color_hex
        )
    color_display.short_description = 'Color'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'parent', 'project', 'client', 'employee', 'created_by'
        )


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'folder', 'file_type', 'formatted_size', 'uploaded_by',
        'is_public', 'created_at'
    ]
    list_filter = [
        'file_type', 'is_public', 'created_at', 'uploaded_by', 'mime_type'
    ]
    search_fields = ['name', 'original_name', 'description', 'file_link']
    readonly_fields = [
        'size', 'formatted_size', 'extension', 'file_link',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('File Information', {
            'fields': ('name', 'original_name', 'file_path', 'folder')
        }),
        ('File Details', {
            'fields': ('file_type', 'size', 'formatted_size', 'mime_type', 'extension')
        }),
        ('Metadata', {
            'fields': ('description', 'uploaded_by', 'is_public')
        }),
        ('Sharing', {
            'fields': ('file_link',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('folder', 'uploaded_by')


@admin.register(FileShare)
class FileShareAdmin(admin.ModelAdmin):
    list_display = [
        'file', 'shared_with', 'shared_by', 'permissions_display', 'created_at'
    ]
    list_filter = ['can_edit', 'can_delete', 'created_at', 'shared_by']
    search_fields = [
        'file__name', 'shared_with__username', 'shared_with__email',
        'shared_by__username'
    ]
    readonly_fields = ['created_at']
    
    def permissions_display(self, obj):
        permissions = []
        if obj.can_edit:
            permissions.append('<span style="color: orange;">Edit</span>')
        if obj.can_delete:
            permissions.append('<span style="color: red;">Delete</span>')
        
        if permissions:
            return format_html(' | '.join(permissions))
        return format_html('<span style="color: green;">View Only</span>')
    permissions_display.short_description = 'Permissions'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'file', 'shared_with', 'shared_by'
        )