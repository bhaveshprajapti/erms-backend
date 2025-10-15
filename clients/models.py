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
    
    # Dates
    date = models.DateField(auto_now_add=True)
    valid_until = models.DateField()
    
    # Financial details
    line_items = models.JSONField(default=list)  # Store line items as JSON
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Status and tracking
    status = models.ForeignKey(StatusChoice, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'category': 'quotation_status'})
    is_converted = models.BooleanField(default=False)  # Track if quotation was converted to project
    converted_project = models.OneToOneField(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='source_quotation')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def generate_quotation_no(self):
        """Generate auto-incremented quotation number starting with QT0001"""
        if self.quotation_no:
            return self.quotation_no
        
        # Get the highest existing quotation_no number
        import re
        from django.db.models import Max
        
        latest_quotation = Quotation.objects.filter(
            quotation_no__regex=r'^QT\d{4}$'
        ).aggregate(Max('quotation_no'))['quotation_no__max']
        
        if latest_quotation:
            # Extract number and increment
            number = int(latest_quotation[2:]) + 1
        else:
            # Start with 1 if no existing quotations
            number = 1
        
        return f"QT{number:04d}"
    
    def calculate_totals(self):
        """Calculate subtotal, tax, and total based on line items"""
        if not self.line_items:
            self.subtotal = 0
            self.tax_amount = 0
            self.total_amount = 0
            return
        
        # Calculate subtotal from line items
        subtotal = sum(
            item.get('quantity', 0) * item.get('rate', 0) 
            for item in self.line_items
        )
        
        self.subtotal = subtotal
        self.tax_amount = subtotal * (self.tax_rate / 100)
        self.total_amount = subtotal + self.tax_amount - self.discount
    
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

