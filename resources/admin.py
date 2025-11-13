from django.contrib import admin
from django.utils.html import format_html
from .models import Equipment, Inventory, ResourceAllocation


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = [
        'type', 'serial_number', 'status_display', 'location', 'purchase_date',
        'warranty_end', 'organization', 'created_at'
    ]
    list_filter = ['status', 'type', 'purchase_date', 'warranty_end', 'organization', 'created_at']
    search_fields = ['type', 'serial_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Equipment Information', {
            'fields': ('type', 'serial_number', 'status', 'organization')
        }),
        ('Location & Dates', {
            'fields': ('location', 'purchase_date', 'warranty_end')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        if obj.status:
            color_map = {
                'available': 'green',
                'allocated': 'blue',
                'maintenance': 'orange',
                'damaged': 'red',
                'retired': 'gray'
            }
            color = color_map.get(obj.status.name.lower(), 'gray')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, obj.status.name
            )
        return format_html('<span style="color: gray;">No Status</span>')
    status_display.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('status', 'location', 'organization')


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = [
        'item_name', 'quantity', 'threshold', 'stock_status', 'organization', 'updated_at'
    ]
    list_filter = ['organization', 'created_at', 'updated_at']
    search_fields = ['item_name']
    readonly_fields = ['created_at', 'updated_at', 'stock_status']
    
    fieldsets = (
        ('Inventory Information', {
            'fields': ('item_name', 'quantity', 'threshold', 'organization')
        }),
        ('Status', {
            'fields': ('stock_status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    def stock_status(self, obj):
        if obj.quantity <= 0:
            return format_html('<span style="color: red; font-weight: bold;">Out of Stock</span>')
        elif obj.quantity <= obj.threshold:
            return format_html('<span style="color: orange; font-weight: bold;">Low Stock</span>')
        else:
            return format_html('<span style="color: green; font-weight: bold;">In Stock</span>')
    stock_status.short_description = 'Stock Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization')


@admin.register(ResourceAllocation)
class ResourceAllocationAdmin(admin.ModelAdmin):
    list_display = [
        'project', 'user', 'equipment', 'allocation_type', 'start_date',
        'end_date', 'duration_display', 'created_at'
    ]
    list_filter = [
        'allocation_type', 'start_date', 'end_date', 'created_at',
        'project', 'user'
    ]
    search_fields = [
        'project__project_name', 'user__username', 'equipment__type',
        'equipment__serial_number'
    ]
    readonly_fields = ['created_at', 'updated_at', 'duration_display']
    
    fieldsets = (
        ('Allocation Information', {
            'fields': ('project', 'user', 'equipment', 'allocation_type')
        }),
        ('Timeline', {
            'fields': ('start_date', 'end_date', 'duration', 'duration_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    def duration_display(self, obj):
        if obj.duration:
            days = obj.duration.days
            hours = obj.duration.seconds // 3600
            return format_html(
                '<span style="color: blue; font-weight: bold;">{} days, {} hours</span>',
                days, hours
            )
        elif obj.start_date and obj.end_date:
            duration = obj.end_date - obj.start_date
            return format_html(
                '<span style="color: green; font-weight: bold;">{} days</span>',
                duration.days + 1
            )
        return format_html('<span style="color: gray;">Not specified</span>')
    duration_display.short_description = 'Duration'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project', 'user', 'equipment')