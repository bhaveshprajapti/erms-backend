from django.contrib import admin
from django.utils.html import format_html
from .models import LeaveType, LeavePolicy, LeaveBalance, FlexAllowanceType, FlexPolicy, FlexBalance


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_paid', 'is_active', 'created_at']
    list_filter = ['is_paid', 'is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at']


@admin.register(LeavePolicy)
class LeavePolicyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'annual_quota', 'monthly_accrual', 'carry_forward_limit',
        'notice_days', 'max_consecutive', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    filter_horizontal = ['leave_types', 'applicable_roles']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Policy Information', {
            'fields': ('name', 'leave_types', 'applicable_roles', 'is_active')
        }),
        ('Quota & Accrual', {
            'fields': ('annual_quota', 'monthly_accrual', 'carry_forward_limit')
        }),
        ('Rules & Restrictions', {
            'fields': ('notice_days', 'max_consecutive')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'leave_type', 'year', 'opening_balance', 'used',
        'carried_forward', 'remaining_display', 'updated_at'
    ]
    list_filter = ['leave_type', 'year', 'policy', 'updated_at']
    search_fields = ['user__username', 'user__email', 'leave_type__name']
    readonly_fields = ['remaining_display', 'updated_at']
    
    fieldsets = (
        ('Balance Information', {
            'fields': ('user', 'leave_type', 'policy', 'year')
        }),
        ('Balance Details', {
            'fields': ('opening_balance', 'used', 'carried_forward', 'remaining_display')
        }),
        ('Metadata', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    def remaining_display(self, obj):
        remaining = obj.remaining
        color = 'green' if remaining > 5 else 'orange' if remaining > 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, remaining
        )
    remaining_display.short_description = 'Remaining'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'leave_type', 'policy')


@admin.register(FlexAllowanceType)
class FlexAllowanceTypeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'duration_minutes', 'max_per_month', 'flex_type_display',
        'is_active', 'created_at'
    ]
    list_filter = ['is_late', 'is_early', 'is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at']
    
    def flex_type_display(self, obj):
        types = []
        if obj.is_late:
            types.append('<span style="color: red;">Late</span>')
        if obj.is_early:
            types.append('<span style="color: blue;">Early</span>')
        return format_html(' | '.join(types)) if types else '-'
    flex_type_display.short_description = 'Type'


@admin.register(FlexPolicy)
class FlexPolicyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'reset_monthly', 'carry_forward', 'is_active', 'created_at'
    ]
    list_filter = ['reset_monthly', 'carry_forward', 'is_active', 'created_at']
    search_fields = ['name']
    filter_horizontal = ['flex_types', 'applicable_roles']
    readonly_fields = ['created_at']


@admin.register(FlexBalance)
class FlexBalanceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'flex_type', 'year_month', 'opening_count', 'used_count',
        'remaining_display', 'created_at'
    ]
    list_filter = ['flex_type', 'year_month', 'policy', 'created_at']
    search_fields = ['user__username', 'user__email', 'flex_type__name']
    readonly_fields = ['remaining_display', 'created_at']
    
    def remaining_display(self, obj):
        remaining = obj.remaining
        color = 'green' if remaining > 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, remaining
        )
    remaining_display.short_description = 'Remaining'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'flex_type', 'policy')