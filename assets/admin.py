from django.contrib import admin
from django.utils.html import format_html
from .models import Directory, Folder, FileDocument, Expense, Payment, SalaryRecord


@admin.register(Directory)
class DirectoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'path', 'entity_type', 'is_active', 'created_at']
    list_filter = ['entity_type', 'is_active', 'created_at']
    search_fields = ['name', 'path']
    readonly_fields = ['created_at']


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'directory', 'created_at']
    list_filter = ['directory', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent', 'directory')


@admin.register(FileDocument)
class FileDocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'folder', 'tags_count', 'created_at']
    list_filter = ['folder', 'created_at', 'tags']
    search_fields = ['name']
    filter_horizontal = ['tags']
    readonly_fields = ['created_at']
    
    def tags_count(self, obj):
        count = obj.tags.count()
        return format_html(
            '<span style="color: blue; font-weight: bold;">{}</span>',
            count
        )
    tags_count.short_description = 'Tags'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('folder').prefetch_related('tags')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = [
        'type', 'project', 'amount_display', 'purchase_date', 'expiry_date',
        'paid_by', 'status_display', 'created_at'
    ]
    list_filter = ['type', 'paid_by', 'status', 'purchase_date', 'created_at']
    search_fields = ['type', 'project__project_name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Expense Information', {
            'fields': ('project', 'type', 'amount', 'paid_by')
        }),
        ('Dates', {
            'fields': ('purchase_date', 'expiry_date')
        }),
        ('Details & Status', {
            'fields': ('details', 'status')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def amount_display(self, obj):
        return format_html(
            '<span style="color: red; font-weight: bold;">₹{:,.2f}</span>',
            obj.amount
        )
    amount_display.short_description = 'Amount'
    
    def status_display(self, obj):
        if obj.status:
            color_map = {
                'pending': 'orange',
                'approved': 'green',
                'rejected': 'red',
                'paid': 'blue'
            }
            color = color_map.get(obj.status.name.lower(), 'gray')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, obj.status.name
            )
        return format_html('<span style="color: gray;">No Status</span>')
    status_display.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project', 'status')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'recipient', 'project', 'amount_display', 'date', 'method',
        'status_display', 'created_at'
    ]
    list_filter = ['method', 'status', 'date', 'created_at']
    search_fields = ['recipient__username', 'project__project_name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('recipient', 'project', 'amount', 'date', 'method')
        }),
        ('Details & Status', {
            'fields': ('details', 'status')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def amount_display(self, obj):
        return format_html(
            '<span style="color: green; font-weight: bold;">₹{:,.2f}</span>',
            obj.amount
        )
    amount_display.short_description = 'Amount'
    
    def status_display(self, obj):
        if obj.status:
            color_map = {
                'pending': 'orange',
                'completed': 'green',
                'failed': 'red',
                'cancelled': 'gray'
            }
            color = color_map.get(obj.status.name.lower(), 'gray')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, obj.status.name
            )
        return format_html('<span style="color: gray;">No Status</span>')
    status_display.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('recipient', 'project', 'status')


@admin.register(SalaryRecord)
class SalaryRecordAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'period_display', 'gross_amount_display', 'net_amount_display',
        'paid_date', 'status_display', 'created_at'
    ]
    list_filter = ['status', 'period_start', 'paid_date', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Salary Information', {
            'fields': ('user', 'period_start', 'period_end')
        }),
        ('Financial Details', {
            'fields': ('gross_amount', 'deductions', 'net_amount')
        }),
        ('Payment Status', {
            'fields': ('paid_date', 'status')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def period_display(self, obj):
        return f"{obj.period_start} to {obj.period_end}"
    period_display.short_description = 'Period'
    
    def gross_amount_display(self, obj):
        return format_html(
            '<span style="color: blue; font-weight: bold;">₹{:,.2f}</span>',
            obj.gross_amount
        )
    gross_amount_display.short_description = 'Gross Amount'
    
    def net_amount_display(self, obj):
        return format_html(
            '<span style="color: green; font-weight: bold;">₹{:,.2f}</span>',
            obj.net_amount
        )
    net_amount_display.short_description = 'Net Amount'
    
    def status_display(self, obj):
        if obj.status:
            color_map = {
                'draft': 'gray',
                'pending': 'orange',
                'paid': 'green',
                'cancelled': 'red'
            }
            color = color_map.get(obj.status.name.lower(), 'gray')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, obj.status.name
            )
        return format_html('<span style="color: gray;">No Status</span>')
    status_display.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'status')