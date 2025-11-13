from django.db import models
from accounts.models import User, Organization
from common.models import Address, StatusChoice
from projects.models import Project

class Equipment(models.Model):
    type = models.CharField(max_length=100)
    status = models.ForeignKey(StatusChoice, on_delete=models.SET_NULL, null=True, limit_choices_to={'category': 'equipment_status'})
    location = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    purchase_date = models.DateField()
    warranty_end = models.DateField(null=True, blank=True)
    serial_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['location', 'status'])]

    def __str__(self):
        return f"{self.type} - {self.serial_number}"


class Inventory(models.Model):
    item_name = models.CharField(max_length=100, unique=True)
    quantity = models.PositiveIntegerField()
    threshold = models.PositiveIntegerField()
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['organization', 'item_name'])]

    def __str__(self):
        return self.item_name


class ResourceAllocation(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.SET_NULL, null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    allocation_type = models.CharField(max_length=20)
    duration = models.DurationField(null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'project'])]

    def __str__(self):
        return f"Allocation for {self.project.name}"

