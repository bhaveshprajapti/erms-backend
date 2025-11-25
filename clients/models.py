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
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    date = models.DateField()
    valid_until = models.DateField()
    services = models.JSONField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.ForeignKey(StatusChoice, on_delete=models.SET_NULL, null=True, limit_choices_to={'category': 'quotation_status'})
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['client', 'date'])]

    def __str__(self):
        return self.quotation_no

