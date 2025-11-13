from rest_framework import serializers
from .models import (
    Directory, Folder, FileDocument, Expense, Payment, SalaryRecord
)

class DirectorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Directory
        fields = '__all__'

class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = '__all__'

class FileDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileDocument
        fields = '__all__'

class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    project = serializers.SerializerMethodField()
    recipient = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    computed_status = serializers.SerializerMethodField()
    total_received = serializers.SerializerMethodField()
    
    # Add write-only fields for create/update
    project_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    recipient_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    status_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Payment
        fields = '__all__'

    def get_project(self, obj):
        if obj.project:
            return {
                'id': obj.project.id,
                'project_id': obj.project.project_id,
                'project_name': obj.project.project_name
            }
        return None

    def get_recipient(self, obj):
        if obj.recipient:
            return {
                'id': obj.recipient.id,
                'first_name': obj.recipient.first_name,
                'last_name': obj.recipient.last_name,
                'username': obj.recipient.username
            }
        return None

    def get_status(self, obj):
        if obj.status:
            return {
                'id': obj.status.id,
                'name': obj.status.name
            }
        return None
    
    def get_total_received(self, obj):
        """Get total received payments for this project"""
        if not obj.project:
            return float(obj.amount)
            
        # Get total received payments for this project
        from django.db.models import Sum
        total_received = obj.__class__.objects.filter(
            project=obj.project,
            recipient__isnull=True  # Only client payments (not developer payments)
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return float(total_received)
    
    def get_remaining_amount(self, obj):
        """Calculate remaining amount for projects"""
        if not obj.project:
            return None
            
        # Get project's approval amount
        approval_amount = obj.project.approval_amount or 0
        total_received = self.get_total_received(obj)
        
        # Calculate remaining amount
        remaining = float(approval_amount) - total_received
        return max(0, remaining)  # Don't return negative amounts
    
    def get_computed_status(self, obj):
        """Compute status based on approval amount and received payments"""
        if not obj.project:
            # For payments without projects, use the actual status
            if obj.status:
                return {
                    'id': obj.status.id,
                    'name': obj.status.name
                }
            return {'id': None, 'name': 'Pending'}
            
        approval_amount = float(obj.project.approval_amount or 0)
        total_received = self.get_total_received(obj)
        
        # If approval amount is 0, any payment is considered "Advanced"
        if approval_amount == 0:
            return {'id': None, 'name': 'Advanced'}
        
        # If we have received payments equal to or more than approval amount, it's "Received"
        if total_received >= approval_amount:
            return {'id': None, 'name': 'Received'}
        # If we have received some payment but less than approval amount, it's "Advanced"
        elif total_received > 0:
            return {'id': None, 'name': 'Advanced'}
        else:
            return {'id': None, 'name': 'Pending'}
    
    def create(self, validated_data):
        # Handle the write-only fields
        project_id = validated_data.pop('project_id', None)
        recipient_id = validated_data.pop('recipient_id', None)
        status_id = validated_data.pop('status_id', None)
        
        # Handle project field from frontend
        if 'project' in validated_data:
            project_id = validated_data.pop('project')
        
        # Handle recipient field from frontend
        if 'recipient' in validated_data:
            recipient_id = validated_data.pop('recipient')
            
        # Handle status field from frontend
        if 'status' in validated_data:
            status_id = validated_data.pop('status')
        
        # Set the foreign key fields
        if project_id is not None and project_id != '':
            try:
                validated_data['project_id'] = int(project_id) if project_id else None
            except (ValueError, TypeError):
                validated_data['project_id'] = None
        
        if recipient_id is not None and recipient_id != '':
            try:
                validated_data['recipient_id'] = int(recipient_id) if recipient_id else None
            except (ValueError, TypeError):
                validated_data['recipient_id'] = None
        
        if status_id is not None and status_id != '':
            try:
                validated_data['status_id'] = int(status_id) if status_id else None
            except (ValueError, TypeError):
                validated_data['status_id'] = None
            
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Handle the write-only fields
        project_id = validated_data.pop('project_id', None)
        recipient_id = validated_data.pop('recipient_id', None)
        status_id = validated_data.pop('status_id', None)
        
        # Handle project field from frontend
        if 'project' in validated_data:
            project_id = validated_data.pop('project')
        
        # Handle recipient field from frontend
        if 'recipient' in validated_data:
            recipient_id = validated_data.pop('recipient')
            
        # Handle status field from frontend
        if 'status' in validated_data:
            status_id = validated_data.pop('status')
        
        # Set the foreign key fields
        if project_id is not None and project_id != '':
            try:
                instance.project_id = int(project_id) if project_id else None
            except (ValueError, TypeError):
                instance.project_id = None
        elif project_id == '':
            instance.project_id = None
        
        if recipient_id is not None and recipient_id != '':
            try:
                instance.recipient_id = int(recipient_id) if recipient_id else None
            except (ValueError, TypeError):
                instance.recipient_id = None
        elif recipient_id == '':
            instance.recipient_id = None
        
        if status_id is not None and status_id != '':
            try:
                instance.status_id = int(status_id) if status_id else None
            except (ValueError, TypeError):
                instance.status_id = None
        elif status_id == '':
            instance.status_id = None
            
        return super().update(instance, validated_data)

class SalaryRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryRecord
        fields = '__all__'
