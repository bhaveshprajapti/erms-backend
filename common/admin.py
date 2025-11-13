from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Address, StatusChoice, Priority, Tag, ProjectType, EmployeeType,
    Designation, Technology, Shift, Holiday, AppService
)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['line1', 'city', 'state', 'country', 'pincode', 'type', 'is_primary']
    list_filter = ['type', 'is_primary', 'country', 'state', 'created_at']
    search_fields = ['line1', 'line2', 'city', 'state', 'pincode']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Address Details', {
            'fields': ('line1', 'line2', 'city', 'state', 'country', 'pincode')
        }),
        ('Classification', {
            'fields': ('type', 'is_primary')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(StatusChoice)
class StatusChoiceAdmin(admin.ModelAdmin):
    list_display = ['category', 'name', 'color_preview', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['category', 'name']
    
    def color_preview(self, obj):
        if obj.color_code:
            return format_html(
                '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; display: inline-block;"></div> {}',
                obj.color_code,
                obj.color_code
            )
        return '-'
    color_preview.short_description = 'Color'


@admin.register(Priority)
class PriorityAdmin(admin.ModelAdmin):
    list_display = ['name', 'level']
    ordering = ['level']
    search_fields = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_preview']
    search_fields = ['name']
    
    def color_preview(self, obj):
        if obj.color_code:
            return format_html(
                '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; display: inline-block;"></div> {}',
                obj.color_code,
                obj.color_code
            )
        return '-'
    color_preview.short_description = 'Color'


@admin.register(ProjectType)
class ProjectTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name', 'description']


@admin.register(EmployeeType)
class EmployeeTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ['title', 'level', 'is_active', 'created_at']
    list_filter = ['is_active', 'level', 'created_at']
    search_fields = ['title']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['level', 'title']


@admin.register(Technology)
class TechnologyAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'created_at']
    list_filter = ['is_active', 'category', 'created_at']
    search_fields = ['name', 'description', 'category']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Technology Details', {
            'fields': ('name', 'description', 'category', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_time', 'end_time', 'is_overnight', 'is_active', 'created_at']
    list_filter = ['is_overnight', 'is_active', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('start_time')


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ['date', 'title', 'description', 'created_at']
    list_filter = ['date', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'
    ordering = ['-date']


@admin.register(AppService)
class AppServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Service Details', {
            'fields': ('name', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )