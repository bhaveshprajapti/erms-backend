from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    LeaveType, LeaveTypePolicy, LeaveBalance, LeaveApplication,
    LeaveApplicationComment, LeaveCalendar, OverallLeavePolicy,
    LeaveBlackoutDate, LeaveBalanceAudit, FlexibleTimingType,
    FlexibleTimingRequest, FlexibleTimingBalance, FlexibleTimingPolicy
)


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_paid', 'color_display', 'is_active', 'created_at']
    list_filter = ['is_paid', 'is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; display: inline-block; border-radius: 3px;"></div> {}',
            obj.color_code,
            obj.color_code
        )
    color_display.short_description = 'Color'


@admin.register(LeaveTypePolicy)
class LeaveTypePolicyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'leave_type', 'annual_quota', 'accrual_rate', 'requires_approval',
        'is_active', 'effective_from'
    ]
    list_filter = [
        'leave_type', 'requires_approval', 'is_active', 'effective_from',
        'accrual_frequency', 'applicable_gender'
    ]
    search_fields = ['name', 'leave_type__name']
    filter_horizontal = ['applicable_roles']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Policy Information', {
            'fields': ('name', 'leave_type', 'applicable_roles', 'applicable_gender')
        }),
        ('Allocation & Accrual', {
            'fields': ('annual_quota', 'accrual_frequency', 'accrual_rate')
        }),
        ('Usage Limits', {
            'fields': (
                'max_per_week', 'max_per_month', 'max_per_year', 'max_consecutive_days'
            )
        }),
        ('Approval Requirements', {
            'fields': ('min_notice_days', 'requires_approval', 'auto_approve_threshold')
        }),
        ('Carry Forward', {
            'fields': ('carry_forward_enabled', 'carry_forward_limit', 'carry_forward_expiry_months')
        }),
        ('Eligibility', {
            'fields': ('min_tenure_days', 'available_during_probation')
        }),
        ('Calendar Settings', {
            'fields': ('include_weekends', 'include_holidays')
        }),
        ('Effective Period', {
            'fields': ('is_active', 'effective_from', 'effective_to')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'leave_type', 'year', 'total_available', 'used_balance',
        'remaining_balance', 'last_accrual_date'
    ]
    list_filter = ['leave_type', 'year', 'policy', 'last_accrual_date']
    search_fields = ['user__username', 'user__email', 'leave_type__name']
    readonly_fields = ['total_available', 'remaining_balance', 'pending_balance', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Balance Information', {
            'fields': ('user', 'leave_type', 'policy', 'year')
        }),
        ('Balance Details', {
            'fields': (
                'opening_balance', 'accrued_balance', 'used_balance',
                'carried_forward', 'adjustment'
            )
        }),
        ('Calculated Values', {
            'fields': ('total_available', 'remaining_balance', 'pending_balance'),
            'classes': ('collapse',)
        }),
        ('Usage Tracking', {
            'fields': ('used_this_week', 'used_this_month'),
            'classes': ('collapse',)
        }),
        ('Tracking Dates', {
            'fields': ('last_accrual_date', 'last_reset_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LeaveApplication)
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'leave_type', 'start_date', 'end_date', 'total_days',
        'status_display', 'approved_by', 'applied_at'
    ]
    list_filter = [
        'status', 'leave_type', 'is_half_day', 'start_date', 'applied_at', 'approved_at'
    ]
    search_fields = [
        'user__username', 'user__email', 'leave_type__name', 'reason'
    ]
    readonly_fields = ['total_days', 'applied_at', 'updated_at']
    
    fieldsets = (
        ('Application Details', {
            'fields': ('user', 'leave_type', 'policy')
        }),
        ('Leave Period', {
            'fields': (
                'start_date', 'end_date', 'total_days', 'is_half_day', 'half_day_period'
            )
        }),
        ('Application Information', {
            'fields': ('reason', 'emergency_contact', 'emergency_phone', 'work_handover')
        }),
        ('Status & Approval', {
            'fields': ('status', 'approved_by', 'approved_at', 'rejection_reason', 'admin_comments')
        }),
        ('Attachment', {
            'fields': ('attachment',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('applied_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        color_map = {
            'draft': 'gray',
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'cancelled': 'purple',
            'expired': 'brown'
        }
        color = color_map.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'


@admin.register(LeaveApplicationComment)
class LeaveApplicationCommentAdmin(admin.ModelAdmin):
    list_display = ['application', 'user', 'comment_preview', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at', 'user']
    search_fields = ['application__user__username', 'user__username', 'comment']
    readonly_fields = ['created_at']
    
    def comment_preview(self, obj):
        return obj.comment[:100] + '...' if len(obj.comment) > 100 else obj.comment
    comment_preview.short_description = 'Comment'


@admin.register(LeaveCalendar)
class LeaveCalendarAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'leave_application', 'is_half_day', 'half_day_period']
    list_filter = ['date', 'is_half_day', 'half_day_period']
    search_fields = ['user__username', 'leave_application__leave_type__name']
    date_hierarchy = 'date'


@admin.register(OverallLeavePolicy)
class OverallLeavePolicyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'max_total_per_week', 'max_total_per_month', 'max_total_per_year',
        'is_active', 'effective_from'
    ]
    list_filter = ['is_active', 'effective_from', 'effective_to']
    search_fields = ['name']
    filter_horizontal = ['applicable_roles']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(LeaveBlackoutDate)
class LeaveBlackoutDateAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'reason', 'is_active', 'created_at']
    list_filter = ['is_active', 'start_date', 'end_date', 'created_at']
    search_fields = ['name', 'reason']
    filter_horizontal = ['applicable_roles', 'applicable_leave_types']
    readonly_fields = ['created_at']
    date_hierarchy = 'start_date'


@admin.register(LeaveBalanceAudit)
class LeaveBalanceAuditAdmin(admin.ModelAdmin):
    list_display = [
        'balance', 'action', 'old_balance', 'new_balance', 'change_amount',
        'performed_by', 'created_at'
    ]
    list_filter = ['action', 'created_at', 'performed_by']
    search_fields = ['balance__user__username', 'reason', 'reference_id']
    readonly_fields = ['created_at']


@admin.register(FlexibleTimingType)
class FlexibleTimingTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'max_duration_minutes', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(FlexibleTimingRequest)
class FlexibleTimingRequestAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'timing_type', 'request_date', 'timing_choice', 'duration_minutes',
        'status_display', 'approved_by', 'created_at'
    ]
    list_filter = [
        'status', 'timing_type', 'timing_choice', 'request_date', 'created_at'
    ]
    search_fields = ['user__username', 'timing_type__name', 'reason']
    readonly_fields = ['created_at', 'updated_at']
    
    def status_display(self, obj):
        color_map = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'cancelled': 'purple'
        }
        color = color_map.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'


@admin.register(FlexibleTimingBalance)
class FlexibleTimingBalanceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'timing_type', 'year_month', 'monthly_quota', 'used_count',
        'remaining_balance'
    ]
    list_filter = ['timing_type', 'year_month']
    search_fields = ['user__username', 'timing_type__name']
    readonly_fields = ['remaining_balance', 'created_at', 'updated_at']


@admin.register(FlexibleTimingPolicy)
class FlexibleTimingPolicyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'max_requests_per_month', 'min_notice_hours', 'requires_approval',
        'is_active', 'effective_from'
    ]
    list_filter = ['requires_approval', 'is_active', 'effective_from']
    search_fields = ['name']
    filter_horizontal = ['applicable_roles', 'allowed_timing_types']
    readonly_fields = ['created_at', 'updated_at']