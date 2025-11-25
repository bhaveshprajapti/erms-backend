from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Project, Task, TimeLog, TaskComment

# indrajit start

from .models import ProjectDetails,AmountPayable,AmountReceived

# indrajit end

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        'project_id', 'project_name', 'client_name', 'project_type', 
        'status', 'start_date', 'deadline', 'payment_value', 
        'payment_status', 'team_members_count', 'created_at'
    ]
    list_filter = [
        'status', 'project_type', 'payment_status', 'start_date', 
        'deadline', 'created_at', 'technologies', 'app_mode'
    ]
    search_fields = [
        'project_id', 'project_name', 'client_name', 'lead_source',
        'quotation__quotation_no', 'client__name'
    ]
    readonly_fields = ['project_id', 'total_expenses', 'profit_loss', 'created_at', 'updated_at']
    filter_horizontal = ['technologies', 'app_mode', 'team_members']
    
    fieldsets = (
        ('Project Information', {
            'fields': (
                'project_id', 'project_name', 'project_type', 'status',
                'start_date', 'deadline', 'completed_date'
            )
        }),
        ('Client & Quotation', {
            'fields': (
                'quotation', 'client', 'client_name', 'client_industry',
                'inquiry_date', 'lead_source'
            )
        }),
        ('Quotation Details', {
            'fields': (
                'quotation_sent', 'demo_given', 'quotation_amount',
                'approval_amount', 'contract_signed'
            ),
            'classes': ('collapse',)
        }),
        ('Technical Details', {
            'fields': ('technologies', 'app_mode', 'team_members')
        }),
        ('Financial Information', {
            'fields': (
                'payment_value', 'payment_status', 'total_expenses', 'profit_loss'
            )
        }),
        ('Expenses Breakdown', {
            'fields': (
                'other_expense', 'developer_charge', 'server_charge',
                'third_party_api_charge', 'mediator_charge', 'domain_charge'
            ),
            'classes': ('collapse',)
        }),
        ('Links & Resources', {
            'fields': (
                'live_link', 'frontend_link', 'backend_link',
                'postman_collection', 'data_folder', 'other_link',
                'project_folder'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('free_service', 'notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def team_members_count(self, obj):
        count = obj.team_members.count()
        if count > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">{}</span>',
                count
            )
        return format_html('<span style="color: red;">0</span>')
    team_members_count.short_description = 'Team Size'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'quotation', 'client', 'project_folder'
        ).prefetch_related('technologies', 'app_mode', 'team_members')


class TimeLogInline(admin.TabularInline):
    model = TimeLog
    extra = 0
    readonly_fields = ['created_at']
    fields = ['user', 'start_time', 'end_time', 'notes', 'created_at']


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    readonly_fields = ['created_at']
    fields = ['user', 'text', 'created_at']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'project', 'assigned_by', 'status', 'priority',
        'start_date', 'due_date', 'progress_percent', 'estimated_hours',
        'assigned_to_count', 'created_at'
    ]
    list_filter = [
        'status', 'priority', 'start_date', 'due_date', 'created_at',
        'project', 'assigned_by'
    ]
    search_fields = ['title', 'description', 'project__project_name', 'assigned_by__username']
    filter_horizontal = ['assigned_to', 'tags']
    inlines = [TimeLogInline, TaskCommentInline]
    
    fieldsets = (
        ('Task Information', {
            'fields': ('title', 'description', 'project', 'assigned_by')
        }),
        ('Assignment & Status', {
            'fields': ('assigned_to', 'status', 'priority', 'progress_percent')
        }),
        ('Timeline', {
            'fields': ('start_date', 'due_date', 'estimated_hours')
        }),
        ('Tags & Metadata', {
            'fields': ('tags', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def assigned_to_count(self, obj):
        count = obj.assigned_to.count()
        if count > 0:
            return format_html(
                '<span style="color: blue; font-weight: bold;">{}</span>',
                count
            )
        return format_html('<span style="color: gray;">0</span>')
    assigned_to_count.short_description = 'Assignees'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'project', 'assigned_by', 'status', 'priority'
        ).prefetch_related('assigned_to', 'tags')


@admin.register(TimeLog)
class TimeLogAdmin(admin.ModelAdmin):
    list_display = [
        'task', 'user', 'start_time', 'end_time', 'duration',
        'created_at'
    ]
    list_filter = ['start_time', 'end_time', 'created_at', 'task__project', 'user']
    search_fields = ['task__title', 'user__username', 'notes']
    readonly_fields = ['created_at', 'duration']
    
    def duration(self, obj):
        if obj.start_time and obj.end_time:
            duration = obj.end_time - obj.start_time
            hours = duration.total_seconds() / 3600
            return format_html(
                '<span style="color: green; font-weight: bold;">{:.2f} hrs</span>',
                hours
            )
        return format_html('<span style="color: orange;">In Progress</span>')
    duration.short_description = 'Duration'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('task', 'user')


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'text_preview', 'created_at']
    list_filter = ['created_at', 'task__project', 'user']
    search_fields = ['task__title', 'user__username', 'text']
    readonly_fields = ['created_at']
    
    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = 'Comment Preview'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('task', 'user')
    
# indrajit start

@admin.register(ProjectDetails)
class ProjectDetailAdmin(admin.ModelAdmin):
    list_display = ['project', 'type', 'amount', 'detail_preview', 'created_at']
    list_filter = ['type', 'project']
    search_fields = ['detail', 'project__project_name', 'project__project_id']
    readonly_fields = ['created_at', 'updated_at']

    def detail_preview(self, obj):
        return obj.detail[:50] + '...' if len(obj.detail) > 50 else obj.detail
    detail_preview.short_description = 'Detail'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project')
    
@admin.register(AmountPayable)
class AmountPayableAdmin(admin.ModelAdmin):
    list_display = ['title', 'amount', 'payment_mode', 'manual_paid_to_name','paid_to_employee','date', 'created_at']
    list_filter = ['payment_mode', 'date']
    search_fields = ['title', 'description','manual_paid_to_name']
    fields = ['date', 'title', 'amount', 'payment_mode','manual_paid_to_name', 'paid_to_employee' , 'details_data', 'description', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('paid_to_employee')
    
@admin.register(AmountReceived)
class AmountReceivedAdmin(admin.ModelAdmin):
    list_display = ['title', 'amount', 'client','manual_client_name', 'payment_mode','date', 'created_at']
    list_filter = ['payment_mode', 'date', 'client']
    search_fields = ['title', 'description', 'client__name']
    fields = ['date', 'title', 'amount', 'payment_mode', 'client','manual_client_name', 'details_data', 'description', 'created_at', 'updated_at'] 
    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('client')

# indrajit end