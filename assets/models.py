from django.db import models
from projects.models import Project
from accounts.models import User
from common.models import StatusChoice, Tag

class Directory(models.Model):
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=500, unique=True)
    entity_type = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Folder(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    directory = models.ForeignKey(Directory, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['directory'])]

    def __str__(self):
        return self.name

class FileDocument(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE)
    tags = models.ManyToManyField(Tag, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['folder'])]

    def __str__(self):
        return self.name

class Expense(models.Model):
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    type = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    paid_by = models.CharField(max_length=20)
    details = models.JSONField(null=True, blank=True)
    status = models.ForeignKey(StatusChoice, on_delete=models.SET_NULL, null=True, limit_choices_to={'category': 'expense_status'})
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['project', 'purchase_date'])]

    def __str__(self):
        return f"{self.type} - {self.amount}"

class Payment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    recipient = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    method = models.CharField(max_length=50)
    details = models.JSONField(null=True, blank=True)
    status = models.ForeignKey(StatusChoice, on_delete=models.SET_NULL, null=True, limit_choices_to={'category': 'payment_status'})
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['project', 'date'])]

    def __str__(self):
        return f"Payment of {self.amount} on {self.date}"

class SalaryRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    period_start = models.DateField()
    period_end = models.DateField()
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    deductions = models.JSONField(null=True, blank=True)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_date = models.DateField(null=True, blank=True)
    status = models.ForeignKey(StatusChoice, on_delete=models.SET_NULL, null=True, limit_choices_to={'category': 'salary_status'})
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'period_start'])]

    def __str__(self):
        return f"Salary for {self.user.username} - {self.period_start} to {self.period_end}"

