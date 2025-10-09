from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from .models import (
    LeaveType, LeaveTypePolicy, LeaveBalance, LeaveApplication,
    LeaveApplicationComment, LeaveCalendar, OverallLeavePolicy,
    LeaveBlackoutDate, LeaveBalanceAudit
)
from .services import LeaveBalanceService, LeaveReportService
import csv
import json


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_paid', 'is_active', 'created_at']
    list_filter = ['is_paid', 'is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    prepopulated_fields = {'code': ('name',)}
    ordering = ['name']


@admin.register(LeaveTypePolicy)
class LeaveTypePolicyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'leave_type', 'annual_quota', 'accrual_frequency', 
        'accrual_rate', 'is_active', 'effective_from', 'effective_to'
    ]
    list_filter = [
        'leave_type', 'accrual_frequency', 'is_active', 
        'effective_from', 'applicable_gender'
    ]
    search_fields = ['name', 'leave_type__name']
    filter_horizontal = ['applicable_roles']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'leave_type', 'applicable_roles', 'applicable_gender')
        }),
        ('Allocation & Accrual', {
            'fields': (
                'annual_quota', 'accrual_frequency', 'accrual_rate',
                'carry_forward_enabled', 'carry_forward_limit', 'carry_forward_expiry_months'
            )
        }),
        ('Usage Limits', {
            'fields': (
                'max_per_week', 'max_per_month', 'max_per_year', 'max_consecutive_days'
            )
        }),
        ('Approval & Notice', {
            'fields': (
                'requires_approval', 'auto_approve_threshold', 'min_notice_days'
            )
        }),
        ('Eligibility', {
            'fields': (
                'min_tenure_days', 'available_during_probation',
                'include_weekends', 'include_holidays'
            )
        }),
        ('Active Period', {
            'fields': ('is_active', 'effective_from', 'effective_to')
        }),
    )


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'leave_type', 'year', 'total_available_display', 
        'used_balance', 'remaining_balance_display', 'last_accrual_date'
    ]
    list_filter = [
        'year', 'leave_type', 'user__role', 'user__is_active',
        'last_accrual_date', 'last_reset_date'
    ]
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'leave_type__name']
    readonly_fields = ['total_available_display', 'remaining_balance_display', 'pending_balance_display']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'leave_type', 'year', 'policy')
        }),
        ('Balance Details', {
            'fields': (
                'opening_balance', 'accrued_balance', 'carried_forward', 
                'adjustment', 'used_balance'
            )
        }),
        ('Calculated Balances', {
            'fields': (
                'total_available_display', 'remaining_balance_display', 
                'pending_balance_display'
            )
        }),
        ('Tracking', {
            'fields': ('last_accrual_date', 'last_reset_date')
        }),
    )
    
    actions = ['assign_annual_balances', 'process_accruals', 'export_balances']
    
    def total_available_display(self, obj):
        return f"{obj.total_available} days"
    total_available_display.short_description = 'Total Available'
    
    def remaining_balance_display(self, obj):
        return f"{obj.remaining_balance} days"
    remaining_balance_display.short_description = 'Remaining'
    
    def pending_balance_display(self, obj):
        return f"{obj.pending_balance} days"
    pending_balance_display.short_description = 'After Pending'
    
    def assign_annual_balances(self, request, queryset):
        """Admin action to assign annual balances"""
        user_ids = list(queryset.values_list('user_id', flat=True).distinct())
        year = timezone.now().year
        
        summary = LeaveBalanceService.assign_annual_balances(
            year=year,
            user_ids=user_ids,
            force_reset=False
        )
        
        messages.success(
            request, 
            f"Assigned balances: {summary['balances_created']} created, "
            f"{summary['balances_updated']} updated, {summary['balances_skipped']} skipped"
        )
    assign_annual_balances.short_description = "Assign annual balances for selected users"
    
    def process_accruals(self, request, queryset):
        """Admin action to process monthly accruals"""
        user_ids = list(queryset.values_list('user_id', flat=True).distinct())
        
        summary = LeaveBalanceService.process_monthly_accruals(
            user_ids=user_ids
        )
        
        messages.success(
            request,
            f"Processed accruals: {summary['processed']} balances updated, "
            f"{summary['skipped']} skipped"
        )
    process_accruals.short_description = "Process monthly accruals for selected users"
    
    def export_balances(self, request, queryset):
        """Admin action to export balance data as CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="leave_balances.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Username', 'Full Name', 'Leave Type', 'Year', 
            'Opening Balance', 'Accrued', 'Carried Forward', 'Adjustment',
            'Total Available', 'Used', 'Remaining'
        ])
        
        for balance in queryset:
            writer.writerow([
                balance.user.username,
                balance.user.get_full_name(),
                balance.leave_type.name,
                balance.year,
                balance.opening_balance,
                balance.accrued_balance,
                balance.carried_forward,
                balance.adjustment,
                balance.total_available,
                balance.used_balance,
                balance.remaining_balance
            ])
        
        return response
    export_balances.short_description = "Export selected balances as CSV"


@admin.register(LeaveApplication)
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'leave_type', 'start_date', 'end_date', 'total_days',
        'status', 'applied_at', 'approved_by'
    ]
    list_filter = [
        'status', 'leave_type', 'start_date', 'applied_at',
        'is_half_day'
    ]
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name',
        'leave_type__name', 'reason'
    ]
    readonly_fields = ['applied_at', 'updated_at']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Application Details', {
            'fields': (
                'user', 'leave_type', 'policy', 'start_date', 'end_date',
                'total_days', 'is_half_day', 'half_day_period'
            )
        }),
        ('Reason & Emergency Contact', {
            'fields': (
                'reason', 'emergency_contact', 'emergency_phone', 'work_handover'
            )
        }),
        ('Status & Approval', {
            'fields': (
                'status', 'approved_by', 'approved_at', 'rejection_reason',
                'admin_comments'
            )
        }),
        ('Tracking', {
            'fields': ('applied_at', 'updated_at', 'attachment')
        }),
    )
    
    actions = ['approve_applications', 'reject_applications']
    
    def approve_applications(self, request, queryset):
        """Admin action to approve selected applications"""
        approved_count = 0
        for application in queryset.filter(status='pending'):
            application.approve(request.user, "Approved via admin")
            approved_count += 1
            
        messages.success(request, f"Approved {approved_count} applications")
    approve_applications.short_description = "Approve selected pending applications"
    
    def reject_applications(self, request, queryset):
        """Admin action to reject selected applications"""
        rejected_count = 0
        for application in queryset.filter(status='pending'):
            application.reject(request.user, "Rejected via admin", "Batch rejection")
            rejected_count += 1
            
        messages.success(request, f"Rejected {rejected_count} applications")
    reject_applications.short_description = "Reject selected pending applications"


@admin.register(OverallLeavePolicy)
class OverallLeavePolicyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'max_total_per_month', 'max_total_per_week', 
        'is_active', 'effective_from', 'effective_to'
    ]
    list_filter = ['is_active', 'effective_from', 'allow_emergency_leave']
    search_fields = ['name']
    filter_horizontal = ['applicable_roles']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'applicable_roles')
        }),
        ('Total Leave Limits', {
            'fields': (
                'max_total_per_week', 'max_total_per_month', 'max_total_per_year'
            )
        }),
        ('Consecutive & Gap Restrictions', {
            'fields': (
                'max_total_consecutive_days', 'min_gap_between_leaves'
            )
        }),
        ('Advance Booking', {
            'fields': (
                'max_advance_booking_days', 'min_advance_booking_days'
            )
        }),
        ('Simultaneous Leave Limits', {
            'fields': (
                'max_simultaneous_leaves_in_team', 'max_simultaneous_leaves_in_department'
            )
        }),
        ('Emergency Leave', {
            'fields': ('allow_emergency_leave', 'emergency_leave_max_days')
        }),
        ('Weekend/Holiday Restrictions', {
            'fields': (
                'block_leave_before_weekend', 'block_leave_after_weekend',
                'block_leave_before_holiday', 'block_leave_after_holiday'
            )
        }),
        ('Active Period', {
            'fields': ('is_active', 'effective_from', 'effective_to')
        }),
    )


@admin.register(LeaveBlackoutDate)
class LeaveBlackoutDateAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_active', 'created_at']
    list_filter = ['is_active', 'start_date', 'created_at']
    search_fields = ['name', 'reason']
    filter_horizontal = ['applicable_roles', 'applicable_leave_types']
    date_hierarchy = 'start_date'


@admin.register(LeaveBalanceAudit)
class LeaveBalanceAuditAdmin(admin.ModelAdmin):
    list_display = [
        'balance', 'action', 'change_amount', 'performed_by', 'created_at'
    ]
    list_filter = ['action', 'created_at', 'balance__leave_type']
    search_fields = [
        'balance__user__username', 'reason', 'reference_id'
    ]
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False  # Audit records are created automatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Audit records should not be modified


@admin.register(LeaveApplicationComment)
class LeaveApplicationCommentAdmin(admin.ModelAdmin):
    list_display = ['application', 'user', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['application__user__username', 'comment']
    readonly_fields = ['created_at']


@admin.register(LeaveCalendar)
class LeaveCalendarAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'leave_application', 'is_half_day']
    list_filter = ['date', 'is_half_day', 'half_day_period']
    search_fields = ['user__username', 'leave_application__leave_type__name']
    date_hierarchy = 'date'
    readonly_fields = ['user', 'leave_application', 'date']  # These are auto-populated
