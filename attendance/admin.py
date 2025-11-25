from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Attendance, LeaveRequest, TimeAdjustment, Approval, SessionLog,UserAttendanceSetting


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'date', 'total_hours_display', 'day_status_display',
        'late_checkin_display','day_ended', 'sessions_count', 'admin_reset_count', 'created_at'
    ]
    list_filter = [
        'day_ended', 'day_status','late_checkin', 'date', 'created_at', 'admin_reset_count'
    ]
    search_fields = ['user__username', 'user__email', 'notes']
    readonly_fields = [
        'sessions_display', 'total_hours_display', 'total_break_time_display',
        'created_at'
    ]
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Attendance Information', {
            'fields': ('user', 'date', 'day_ended', 'day_end_time')
        }),
        ('Time Tracking', {
            'fields': (
                'total_hours_display', 'total_break_time_display', 'break_start_time'
            )
        }),
        ('Sessions', {
            'fields': ('sessions_display',),
            'classes': ('collapse',)
        }),
        ('Status & Location', {
            'fields': ('day_status', 'location', 'notes')
        }),
        ('Admin Actions', {
            'fields': ('admin_reset_at', 'admin_reset_count'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def sessions_count(self, obj):
        if obj.sessions:
            count = len(obj.sessions)
            return format_html(
                '<span style="color: blue; font-weight: bold;">{}</span>',
                count
            )
        return format_html('<span style="color: gray;">0</span>')
    sessions_count.short_description = 'Sessions'
    
    def total_hours_display(self, obj):
        if obj.total_hours:
            hours = obj.total_hours.total_seconds() / 3600
            color = 'green' if hours >= 8 else 'orange' if hours >= 6 else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.2f} hrs</span>',
                color, hours
            )
        return format_html('<span style="color: gray;">-</span>')
    total_hours_display.short_description = 'Total Hours'
    
    def total_break_time_display(self, obj):
        if obj.total_break_time:
            minutes = obj.total_break_time.total_seconds() / 60
            return format_html(
                '<span style="color: orange;">{:.0f} min</span>',
                minutes
            )
        return format_html('<span style="color: gray;">-</span>')
    total_break_time_display.short_description = 'Break Time'
    
    def day_status_display(self, obj):
        if obj.day_status:
            color_map = {
                'Full Day': 'green',
                'Half Day': 'orange',
                'Short Day': 'red',
                'Absent': 'darkred'
            }
            color = color_map.get(obj.day_status, 'gray')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, obj.day_status
            )
        return format_html('<span style="color: gray;">-</span>')
    day_status_display.short_description = 'Status'

    def late_checkin_display(self, obj):
        if getattr(obj, 'late_checkin', False):
            return format_html('<span style="color: red; font-weight: bold;">Late</span>')
        return format_html('<span style="color: green;">On Time</span>')
    late_checkin_display.short_description = 'Late?'
    
    def sessions_display(self, obj):
        if obj.sessions:
            sessions_html = []
            for i, session in enumerate(obj.sessions, 1):
                check_in = session.get('check_in', 'N/A')
                check_out = session.get('check_out', 'In Progress')
                sessions_html.append(f"Session {i}: {check_in} - {check_out}")
            return format_html('<br>'.join(sessions_html))
        return 'No sessions'
    sessions_display.short_description = 'Sessions Detail'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'leave_type', 'start_date', 'end_date', 'duration_days',
        'status_display', 'approver', 'created_at'
    ]
    list_filter = [
        'status', 'leave_type', 'start_date', 'created_at', 'organization'
    ]
    search_fields = ['user__username', 'reason', 'rejection_reason']
    readonly_fields = ['created_at']
    
    def status_display(self, obj):
        if obj.status:
            color_map = {
                'pending': 'orange',
                'approved': 'green',
                'rejected': 'red'
            }
            color = color_map.get(obj.status.name.lower(), 'gray')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, obj.status.name
            )
        return format_html('<span style="color: gray;">No Status</span>')
    status_display.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'leave_type', 'status', 'approver', 'organization'
        )


@admin.register(TimeAdjustment)
class TimeAdjustmentAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'date', 'flex_type', 'duration_minutes', 'status_display',
        'approved_by', 'created_at'
    ]
    list_filter = ['status', 'flex_type', 'date', 'created_at']
    search_fields = ['user__username', 'description']
    readonly_fields = ['created_at']
    
    def status_display(self, obj):
        if obj.status:
            color_map = {
                'pending': 'orange',
                'approved': 'green',
                'rejected': 'red'
            }
            color = color_map.get(obj.status.name.lower(), 'gray')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, obj.status.name
            )
        return format_html('<span style="color: gray;">No Status</span>')
    status_display.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'flex_type', 'status', 'approved_by', 'attendance'
        )


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = [
        'request_info', 'approver', 'level', 'status_display',
        'is_escalated', 'decided_at', 'created_at'
    ]
    list_filter = ['status', 'level', 'is_escalated', 'decided_at', 'created_at']
    search_fields = ['approver__username', 'comments']
    readonly_fields = ['created_at']
    
    def request_info(self, obj):
        return f"{obj.content_type.model} #{obj.object_id}"
    request_info.short_description = 'Request'
    
    def status_display(self, obj):
        if obj.status:
            color_map = {
                'pending': 'orange',
                'approved': 'green',
                'rejected': 'red'
            }
            color = color_map.get(obj.status.name.lower(), 'gray')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, obj.status.name
            )
        return format_html('<span style="color: gray;">No Status</span>')
    status_display.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'content_type', 'approver', 'status'
        )


@admin.register(SessionLog)
class SessionLogAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'event_type', 'date', 'timestamp', 'session_count',
        'is_session_active', 'last_activity'
    ]
    list_filter = [
        'event_type', 'is_session_active', 'date', 'timestamp'
    ]
    search_fields = ['user__username', 'notes', 'ip_address']
    readonly_fields = ['timestamp', 'last_activity']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('user', 'event_type', 'date', 'session_count')
        }),
        ('Session Status', {
            'fields': ('is_session_active', 'last_activity')
        }),
        ('Location & Network', {
            'fields': ('location', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    


@admin.action(description='Activate Audit Mode for selected users')
def activate_audit_mode(modeladmin, request, queryset):
    """Bulk action to set is_audit_mode_active to True"""
    updated_count = queryset.update(is_audit_mode_active=True)
    modeladmin.message_user(
        request,
        f'{updated_count} users successfully set to Audit Mode Active.', 
        level='success'
    )

@admin.action(description='Deactivate Audit Mode for selected users')
def deactivate_audit_mode(modeladmin, request, queryset):
    """Bulk action to set is_audit_mode_active to False"""
    updated_count = queryset.update(is_audit_mode_active=False)
    modeladmin.message_user(
        request, 
        f'{updated_count} users successfully set to Audit Mode Inactive.', 
        level='success'
    )

@admin.register(UserAttendanceSetting)
class UserAttendanceSettingAdmin(admin.ModelAdmin):
    list_display = ['user','is_audit_mode_active']
    list_filter = ['is_audit_mode_active']
    search_fields = ['user__username','user__firstname', 'user__lastname']
    actions = [activate_audit_mode, deactivate_audit_mode]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')