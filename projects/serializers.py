from rest_framework import serializers
from .models import Project, Task, TimeLog, TaskComment
from accounts.serializers import UserListSerializer
from common.serializers import TechnologySerializer, AppServiceSerializer
from clients.serializers import QuotationListSerializer, ClientListSerializer
from datetime import datetime

# indrajit start
from .models import ProjectDetails,AmountPayable,AmountReceived
from rest_framework.validators import UniqueTogetherValidator
from accounts.models import User
from django.apps import apps
# indrajit end

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

# indrajit start
class ProjectDetailSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.project_name', read_only = True)

    class Meta:
        model = ProjectDetails
        fields = '__all__'

    validators = [
        UniqueTogetherValidator(
            queryset=ProjectDetails.objects.all(),
            fields=['project','type'],
            message="This Project already has a detail entry for the selected type (Frontend/Backend/Design). Please update the existing entry."
        )
    ]

class ClientShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = apps.get_model('clients', 'Client') 
        fields = ['id', 'name', 'email']

class EmployeeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'username', 
            'first_name', 
            'last_name'
        ]

class AmountPayableSerializer(serializers.ModelSerializer):
    # project_name = serializers.CharField(source='project.project_name', read_only=True)

    paid_to_employee_detail = EmployeeShortSerializer(source='paid_to_employee', read_only=True) 

    details = serializers.JSONField(source='details_data', required=False, allow_null=True) 

    class Meta:
        model = AmountPayable
        fields = ['id', 'date', 'title','description', 'amount', 'payment_mode', 'manual_paid_to_name','paid_to_employee', 'paid_to_employee_detail', 'details', 'created_at', 'updated_at']

    def validate(self, data):
        payment_mode = data.get('payment_mode')
        details = data.get('details_data', {})
        
        required_fields = []
        
        if payment_mode == 'Bank':
            required_fields = ['bank_name', ]
        elif payment_mode == 'UPI':
            required_fields = ['upi_id']
        

        missing_fields = [field for field in required_fields if not details.get(field)]
        
        if missing_fields:
            raise serializers.ValidationError({
                'details_data': f"For '{payment_mode}', the following details are required: {', '.join(missing_fields)}"
            })
        
        employee = data.get('paid_to_employee')
        manual_name = data.get('manual_paid_to_name')
        
        if not employee and not manual_name:
             raise serializers.ValidationError({
                 'paid_to_employee': "Either Paid To Employee (FK) or Manual Recipient Name is required for tracking payable amounts."
             })
            
        return data

class AmountReceivedSerializer(serializers.ModelSerializer):
    client_detail = ClientShortSerializer(source='client', read_only=True)

    details = serializers.JSONField(source='details_data', required=False, allow_null=True) 

    class Meta:
        model = AmountReceived 
        fields = ['id', 'date', 'title', 'description', 'amount', 'payment_mode', 'client', 'manual_client_name','client_detail', 'details', 'created_at', 'updated_at']

    def validate(self, data):
        payment_mode = data.get('payment_mode')
        details = data.get('details_data', {})
        
        required_fields = []
        
        if payment_mode == 'Bank':
            required_fields = ['bank_name'] 
        elif payment_mode == 'UPI':
            required_fields = ['upi_id']
        elif payment_mode == 'Cheque':
            required_fields = ['cheque_no'] 

        missing_fields = [field for field in required_fields if not details.get(field)]
        
        if missing_fields:
            raise serializers.ValidationError({
                'details_data': f"For '{payment_mode}', the following receipt details are required: {', '.join(missing_fields)}"
            })
        
        client = data.get('client')
        manual_client_name = data.get('manual_client_name')
            
        if not client and not manual_client_name:
             raise serializers.ValidationError({'client': "Client is required for tracking received amounts."})
             
        return data
# indrajit end
