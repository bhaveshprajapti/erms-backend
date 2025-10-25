from django.db import models
from django.utils import timezone
from accounts.models import User
from common.models import ProjectType, StatusChoice, Technology, Priority, Tag, AppService

class Project(models.Model):
    PROJECT_TYPE_CHOICES = [
        ('Hourly', 'Hourly'),
        ('Fixed', 'Fixed'),
    ]
    
    STATUS_CHOICES = [
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('On Hold', 'On Hold'),
        ('Cancelled', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Advanced', 'Advanced'),
        ('Paid', 'Received'),
    ]
    
    YES_NO_CHOICES = [
        ('Yes', 'Yes'),
        ('No', 'No'),
    ]

    # Auto-generated Project ID
    project_id = models.CharField(max_length=10, unique=True, blank=True)
    
    # Quotation Details
    quotation = models.ForeignKey('clients.Quotation', on_delete=models.SET_NULL, null=True, blank=True)
    client = models.ForeignKey('clients.Client', on_delete=models.SET_NULL, null=True, blank=True)
    inquiry_date = models.DateField(null=True, blank=True)
    lead_source = models.CharField(max_length=255, null=True, blank=True)
    quotation_sent = models.CharField(max_length=3, choices=YES_NO_CHOICES, null=True, blank=True)
    demo_given = models.CharField(max_length=3, choices=YES_NO_CHOICES, null=True, blank=True)
    quotation_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    approval_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    client_industry = models.CharField(max_length=255, null=True, blank=True)
    client_name = models.CharField(max_length=255, null=True, blank=True)
    contract_signed = models.CharField(max_length=3, choices=YES_NO_CHOICES, null=True, blank=True)
    
    # Project Details
    project_name = models.CharField(max_length=255)
    project_type = models.CharField(max_length=10, choices=PROJECT_TYPE_CHOICES, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    technologies = models.ManyToManyField(Technology, blank=True)
    app_mode = models.ManyToManyField(AppService, blank=True, related_name='projects')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='In Progress')
    team_members = models.ManyToManyField(User, related_name='projects', blank=True)
    
    # Payment and Links
    payment_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    live_link = models.URLField(null=True, blank=True)
    postman_collection = models.URLField(null=True, blank=True)
    data_folder = models.URLField(null=True, blank=True)
    other_link = models.URLField(null=True, blank=True)
    frontend_link = models.URLField(null=True, blank=True)
    backend_link = models.URLField(null=True, blank=True)
    
    # Financial Details
    other_expense = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    developer_charge = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    server_charge = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    third_party_api_charge = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    mediator_charge = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    domain_charge = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, default=0)
    
    # Additional Details
    completed_date = models.DateField(null=True, blank=True)
    free_service = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    # Project Folder
    project_folder = models.ForeignKey('files.Folder', on_delete=models.SET_NULL, null=True, blank=True, related_name='project_ref')
    
    # System fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['status', 'start_date'])]
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.project_id:
            self.project_id = self.generate_project_id()
        super().save(*args, **kwargs)
    
    def generate_project_id(self):
        """Generate auto project ID with format P0001, P0002, etc."""
        # Get the highest existing project number
        last_project = Project.objects.filter(
            project_id__startswith='P'
        ).exclude(id=self.id).order_by('-id').first()
        
        if last_project and last_project.project_id:
            try:
                # Extract number from project_id (e.g., P0001 -> 1)
                last_number = int(last_project.project_id[1:])
                next_number = last_number + 1
            except (ValueError, IndexError):
                next_number = 1
        else:
            next_number = 1
        
        return f"P{next_number:04d}"
    
    def __str__(self):
        return f"{self.project_id} - {self.project_name}" if self.project_id else self.project_name
    
    @property
    def total_expenses(self):
        """Calculate total expenses"""
        expenses = [
            self.other_expense or 0,
            self.developer_charge or 0,
            self.server_charge or 0,
            self.third_party_api_charge or 0,
            self.mediator_charge or 0,
            self.domain_charge or 0,
        ]
        return sum(expenses)
    
    @property
    def profit_loss(self):
        """Calculate profit/loss"""
        revenue = self.payment_value or 0
        expenses = self.total_expenses
        return revenue - expenses


class Task(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    assigned_to = models.ManyToManyField(User, related_name='tasks')
    status = models.ForeignKey(StatusChoice, on_delete=models.SET_NULL, null=True, limit_choices_to={'category': 'task_status'})
    priority = models.ForeignKey(Priority, on_delete=models.SET_NULL, null=True)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    progress_percent = models.IntegerField(default=0)
    tags = models.ManyToManyField(Tag, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['project', 'status', 'due_date'])]

    def __str__(self):
        return self.title


class TimeLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['task', 'user'])]

    def __str__(self):
        return f"{self.user.username} on {self.task.title}"


class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['task'])]

    def __str__(self):
        return f"Comment by {self.user.username} on {self.task.title}"

