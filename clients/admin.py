from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Client, ClientRole, Quotation


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'email', 'phone', 'organization', 'status',
        'rating_display', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'status', 'organization', 'rating', 'created_at']
    search_fields = ['name', 'email', 'phone', 'gst_number', 'website']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Client Information', {
            'fields': ('name', 'email', 'phone', 'organization', 'address')
        }),
        ('Business Details', {
            'fields': ('gst_number', 'website', 'status', 'rating')
        }),
        ('File Management', {
            'fields': ('client_folder',),
            'classes': ('collapse',)
        }),
        ('Status & Metadata', {
            'fields': ('is_active', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def rating_display(self, obj):
        if obj.rating > 0:
            stars = '★' * obj.rating + '☆' * (5 - obj.rating)
            return format_html(
                '<span style="color: gold; font-size: 16px;">{}</span> ({})',
                stars, obj.rating
            )
        return format_html('<span style="color: gray;">No rating</span>')
    rating_display.short_description = 'Rating'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'organization', 'address', 'status', 'client_folder'
        )


@admin.register(ClientRole)
class ClientRoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'internal_role', 'permissions_count', 'modules_count', 'is_active']
    list_filter = ['is_active', 'internal_role']
    search_fields = ['name']
    filter_horizontal = ['permissions', 'allowed_modules']
    
    def permissions_count(self, obj):
        count = obj.permissions.count()
        return format_html(
            '<span style="color: blue; font-weight: bold;">{}</span>',
            count
        )
    permissions_count.short_description = 'Permissions'
    
    def modules_count(self, obj):
        count = obj.allowed_modules.count()
        return format_html(
            '<span style="color: green; font-weight: bold;">{}</span>',
            count
        )
    modules_count.short_description = 'Modules'


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = [
        'quotation_no', 'client_info', 'title', 'date', 'valid_until',
        'grand_total_display', 'status', 'is_converted', 'created_at'
    ]
    list_filter = [
        'status', 'is_converted', 'date', 'valid_until', 'created_at',
        'prepared_by', 'lead_source'
    ]
    search_fields = [
        'quotation_no', 'title', 'client_name', 'client_email',
        'client__name', 'client__email', 'lead_source'
    ]
    readonly_fields = [
        'quotation_no', 'subtotal', 'tax_amount', 'discount', 'total_amount',
        'grand_total', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Quotation Details', {
            'fields': (
                'quotation_no', 'title', 'description', 'date', 'valid_until',
                'prepared_by', 'lead_source'
            )
        }),
        ('Client Information', {
            'fields': (
                'client', 'client_name', 'client_email', 'client_phone', 'client_address'
            )
        }),
        ('Service Items', {
            'fields': ('service_items',),
            'classes': ('collapse',)
        }),
        ('Hosting Services', {
            'fields': (
                'domain_registration', 'server_hosting', 'ssl_certificate', 'email_hosting'
            ),
            'classes': ('collapse',)
        }),
        ('Financial Details', {
            'fields': (
                'subtotal', 'tax_rate', 'tax_amount', 'discount_type',
                'discount_value', 'discount', 'total_amount', 'grand_total'
            )
        }),
        ('Terms & Conditions', {
            'fields': ('terms_conditions', 'payment_terms', 'additional_notes'),
            'classes': ('collapse',)
        }),
        ('Signature', {
            'fields': ('signatory_name', 'signatory_designation', 'signature'),
            'classes': ('collapse',)
        }),
        ('Status & Conversion', {
            'fields': ('status', 'is_converted', 'converted_project')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def client_info(self, obj):
        client_data = obj.get_client_info()
        if obj.client:
            url = reverse('admin:clients_client_change', args=[obj.client.id])
            return format_html(
                '<a href="{}">{}</a><br><small>{}</small>',
                url, client_data['name'], client_data['email']
            )
        return format_html(
            '{}<br><small>{}</small>',
            client_data['name'] or 'No Name',
            client_data['email'] or 'No Email'
        )
    client_info.short_description = 'Client'
    
    def grand_total_display(self, obj):
        return format_html(
            '<span style="color: green; font-weight: bold;">₹{:,.2f}</span>',
            obj.grand_total
        )
    grand_total_display.short_description = 'Grand Total'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'client', 'status', 'prepared_by', 'converted_project'
        )