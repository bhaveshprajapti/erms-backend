from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'entity_info', 'user', 'action_display', 'created_at'
    ]
    list_filter = ['entity_type', 'action', 'created_at', 'user']
    search_fields = ['entity_type', 'entity_id', 'user__username']
    readonly_fields = ['created_at', 'old_values_display', 'new_values_display']
    
    fieldsets = (
        ('Audit Information', {
            'fields': ('entity_type', 'entity_id', 'user', 'action')
        }),
        ('Changes', {
            'fields': ('old_values_display', 'new_values_display'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def entity_info(self, obj):
        return format_html(
            '<strong>{}</strong> #{}<br><small>ID: {}</small>',
            obj.entity_type.title(),
            obj.entity_id,
            obj.entity_id
        )
    entity_info.short_description = 'Entity'
    
    def action_display(self, obj):
        color_map = {
            'create': 'green',
            'update': 'blue',
            'delete': 'red',
            'view': 'gray'
        }
        color = color_map.get(obj.action.lower(), 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.action.upper()
        )
    action_display.short_description = 'Action'
    
    def old_values_display(self, obj):
        if obj.old_values:
            import json
            try:
                formatted = json.dumps(obj.old_values, indent=2)
                return format_html('<pre>{}</pre>', formatted)
            except:
                return str(obj.old_values)
        return 'No old values'
    old_values_display.short_description = 'Old Values'
    
    def new_values_display(self, obj):
        if obj.new_values:
            import json
            try:
                formatted = json.dumps(obj.new_values, indent=2)
                return format_html('<pre>{}</pre>', formatted)
            except:
                return str(obj.new_values)
        return 'No new values'
    new_values_display.short_description = 'New Values'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def has_add_permission(self, request):
        # Audit logs should not be manually created
        return False
    
    def has_change_permission(self, request, obj=None):
        # Audit logs should not be modified
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete audit logs
        return request.user.is_superuser