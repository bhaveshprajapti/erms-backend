from django.db import models
from accounts.models import Organization, Role, Permission, Module
from common.models import Address, StatusChoice
from projects.models import Project

class Client(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.OneToOneField(Address, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.ForeignKey(StatusChoice, on_delete=models.SET_NULL, null=True, limit_choices_to={'category': 'client_status'})
    rating = models.PositiveIntegerField(default=0)
    gst_number = models.CharField(max_length=15, null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['email', 'status'])]

    def __str__(self):
        return self.name


class ClientRole(models.Model):
    name = models.CharField(max_length=50, unique=True)
    internal_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    allowed_modules = models.ManyToManyField(Module, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=['name'])]

    def __str__(self):
        return self.name


class Quotation(models.Model):
    quotation_no = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True)
    
    # Client info fields (for quotations without linked client)
    client_name = models.CharField(max_length=255, null=True, blank=True)
    client_email = models.EmailField(null=True, blank=True)
    client_phone = models.CharField(max_length=15, null=True, blank=True)
    client_address = models.TextField(null=True, blank=True)
    
    # Quotation details
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    terms_conditions = models.TextField(null=True, blank=True)
    
    # Additional fields from modal
    prepared_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='prepared_quotations')
    lead_source = models.CharField(max_length=255, null=True, blank=True)
    
    # Dates
    date = models.DateField(auto_now_add=True)
    valid_until = models.DateField()
    
    # Service items and hosting details
    service_items = models.JSONField(default=list)  # Store service items as JSON
    domain_registration = models.JSONField(default=dict)  # Store hosting details as JSON
    server_hosting = models.JSONField(default=dict)
    ssl_certificate = models.JSONField(default=dict)
    email_hosting = models.JSONField(default=dict)
    
    # Financial details
    line_items = models.JSONField(default=list)  # Store line items as JSON (legacy)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_type = models.CharField(max_length=10, choices=[('none', 'None'), ('flat', 'Flat'), ('percent', 'Percent')], default='none')
    discount_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Calculated discount amount
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Final total
    
    # Additional info
    payment_terms = models.TextField(null=True, blank=True)
    additional_notes = models.TextField(null=True, blank=True)
    signatory_name = models.CharField(max_length=255, null=True, blank=True)
    signatory_designation = models.CharField(max_length=255, null=True, blank=True)
    signature = models.ImageField(upload_to='quotation_signatures/', null=True, blank=True)
    
    # Status and tracking
    status = models.ForeignKey(StatusChoice, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'category': 'quotation_status'})
    is_converted = models.BooleanField(default=False)  # Track if quotation was converted to project
    converted_project = models.OneToOneField(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='source_quotation')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def generate_quotation_no(self):
        """Generate quotation number in format: QT-DW-DDMMYYYY-XXXXXX"""
        if self.quotation_no:
            return self.quotation_no
        
        from .utils import ensure_unique_quotation_number
        return ensure_unique_quotation_number()
    
    def calculate_totals(self):
        """Calculate subtotal, tax, and total based on service items and hosting"""
        subtotal = 0
        
        # Calculate service items total
        if self.service_items:
            subtotal += sum(
                item.get('quantity', 0) * item.get('unit_price', 0) 
                for item in self.service_items
            )
        
        # Add hosting items if included
        hosting_items = [self.domain_registration, self.server_hosting, self.ssl_certificate, self.email_hosting]
        for hosting_item in hosting_items:
            if hosting_item and hosting_item.get('included', False):
                subtotal += hosting_item.get('unit_price', 0)
        
        # Apply discount
        discount_amount = 0
        if self.discount_type == 'flat':
            discount_amount = self.discount_value
        elif self.discount_type == 'percent':
            discount_amount = (subtotal * self.discount_value) / 100
        
        # Calculate tax on discounted amount
        after_discount = subtotal - discount_amount
        tax_amount = (after_discount * self.tax_rate) / 100
        grand_total = after_discount + tax_amount
        
        # Update fields
        self.subtotal = subtotal
        self.discount = discount_amount
        self.tax_amount = tax_amount
        self.total_amount = grand_total
        self.grand_total = grand_total
    
    def save(self, *args, **kwargs):
        if not self.quotation_no:
            self.quotation_no = self.generate_quotation_no()
        
        # Auto-calculate totals
        self.calculate_totals()
        
        super().save(*args, **kwargs)
    
    def get_client_info(self):
        """Get client information from linked client or stored fields"""
        if self.client:
            return {
                'name': self.client.name,
                'email': self.client.email,
                'phone': self.client.phone,
                'address': str(self.client.address) if self.client.address else None
            }
        else:
            return {
                'name': self.client_name,
                'email': self.client_email,
                'phone': self.client_phone,
                'address': self.client_address
            }
    
    class Meta:
        indexes = [
            models.Index(fields=['client', 'date']),
            models.Index(fields=['quotation_no']),
            models.Index(fields=['status', 'created_at'])
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.quotation_no} - {self.get_client_info()['name'] or 'No Client'}"

