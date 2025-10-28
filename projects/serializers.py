from rest_framework import serializers
from .models import Project, Task, TimeLog, TaskComment
from accounts.serializers import UserListSerializer
from common.serializers import TechnologySerializer, AppServiceSerializer
from clients.serializers import QuotationListSerializer, ClientListSerializer
from datetime import datetime

class FlexibleDateField(serializers.DateField):
    """Custom date field that accepts multiple formats including DD/MM/YYYY"""
    
    def to_internal_value(self, value):
        if not value:
            return None
            
        if isinstance(value, str):
            # Try DD/MM/YYYY format first
            for date_format in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                try:
                    parsed_date = datetime.strptime(value, date_format).date()
                    return parsed_date
                except ValueError:
                    continue
            
            # If none of the formats work, let the parent handle it
            return super().to_internal_value(value)
        
        return super().to_internal_value(value)

class ProjectSerializer(serializers.ModelSerializer):
    project_id = serializers.CharField(read_only=True)  # Auto-generated, read-only
    technologies_detail = TechnologySerializer(source='technologies', many=True, read_only=True)
    app_mode_detail = AppServiceSerializer(source='app_mode', many=True, read_only=True)
    team_members_detail = UserListSerializer(source='team_members', many=True, read_only=True)
    quotation_detail = QuotationListSerializer(source='quotation', read_only=True)
    client_detail = ClientListSerializer(source='client', read_only=True)
    project_folder_detail = serializers.SerializerMethodField()
    total_expenses = serializers.ReadOnlyField()
    profit_loss = serializers.ReadOnlyField()
    payments = serializers.SerializerMethodField()
    received_payments = serializers.SerializerMethodField()
    
    # Override date fields to use flexible format
    inquiry_date = FlexibleDateField(required=False, allow_null=True)
    start_date = FlexibleDateField(required=False, allow_null=True)
    deadline = FlexibleDateField(required=False, allow_null=True)
    completed_date = FlexibleDateField(required=False, allow_null=True)
    
    def get_project_folder_detail(self, obj):
        if obj.project_folder:
            from files.serializers import FolderListSerializer
            return FolderListSerializer(obj.project_folder).data
        return None
    
    def get_payments(self, obj):
        from assets.models import Payment
        payments = Payment.objects.filter(project=obj).order_by('-date')
        return [{
            'id': payment.id,
            'amount': float(payment.amount),
            'date': payment.date,
            'method': payment.method,
            'details': payment.details,
            'status': {
                'id': payment.status.id,
                'name': payment.status.name
            } if payment.status else None
        } for payment in payments]
    
    def get_received_payments(self, obj):
        from assets.models import Payment
        from django.db.models import Sum
        total = Payment.objects.filter(project=obj).aggregate(Sum('amount'))['amount__sum']
        return float(total) if total else 0
    
    class Meta:
        model = Project
        fields = '__all__'

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'

class TimeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeLog
        fields = '__all__'

class TaskCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskComment
        fields = '__all__'
