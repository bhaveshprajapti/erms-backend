import os
from django.contrib.auth import authenticate
from django.conf import settings
from rest_framework import serializers
from .models import User, Role, ProfileUpdateRequest, Organization, Module, Permission, EmployeePayment
from common.models import Address, Designation, Technology, Shift
from common.serializers import AddressSerializer

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'

class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = '__all__'

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = '__all__'

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'

class UserListSerializer(serializers.ModelSerializer):
    designations = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Designation.objects.filter(is_active=True), required=False
    )
    technologies = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Technology.objects.filter(is_active=True), required=False
    )
    shifts = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Shift.objects.filter(is_active=True), required=False
    )
    
    class Meta:
        model = User
        fields = (
            'id', 'employee_id', 'username', 'first_name', 'last_name', 'email', 'phone',
            'organization', 'role', 'employee_type', 'joining_date', 'is_active', 
            'is_staff', 'is_superuser', 'designations', 'technologies', 'shifts', 'profile_picture'
        )

class UserDetailSerializer(serializers.ModelSerializer):
    designations = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Designation.objects.filter(is_active=True), required=False
    )
    technologies = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Technology.objects.filter(is_active=True), required=False
    )
    shifts = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Shift.objects.filter(is_active=True), required=False
    )
    create_folder = serializers.BooleanField(write_only=True, required=False, default=False)
    
    current_address_text = serializers.CharField(write_only=True, required=False, allow_blank=True)
    permanent_address_text = serializers.CharField(write_only=True, required=False, allow_blank=True)
    document_link = serializers.URLField(required=False, allow_blank=True)
    account_holder = serializers.CharField(required=False, allow_blank=True)
    account_number = serializers.CharField(required=False, allow_blank=True)
    ifsc_code = serializers.CharField(required=False, allow_blank=True)
    branch = serializers.CharField(required=False, allow_blank=True)
    
    # Use AddressSerializer for read operations to return full object
    current_address = AddressSerializer(read_only=True)
    permanent_address = AddressSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'employee_id', 'username', 'password', 'plain_password', 'first_name', 'last_name', 'email', 'phone',
            'organization', 'role', 'employee_type', 'joining_date', 'birth_date',
            'gender', 'marital_status', 'is_active', 'is_staff', 'is_superuser', 'employee_details',
            'emergency_contact', 'emergency_phone', 'salary', 'designations', 'technologies', 'shifts',
            'folder_path', 'create_folder', 'is_on_probation', 'probation_months',
            'is_on_notice_period', 'notice_period_end_date', 'profile_picture',
            'current_address', 'permanent_address', 'current_address_text', 
            'permanent_address_text', 'document_link', 'account_holder', 
            'account_number', 'ifsc_code', 'branch'
        )
        extra_kwargs = {
            'password': {'write_only': True},
            'plain_password': {'write_only': True},
            'folder_path': {'read_only': True},
            'employee_id': {'read_only': True},
            'username': {'read_only': True}
        }

    def validate(self, data):
        """Custom validation for probation and notice period fields"""
        # Validate probation fields
        if data.get('is_on_probation') and not data.get('probation_months'):
            raise serializers.ValidationError({
                'probation_months': 'This field is required when employee is on probation.'
            })
        
        if not data.get('is_on_probation') and data.get('probation_months'):
            # Clear probation_months if not on probation
            data['probation_months'] = None
        
        # Validate notice period fields
        if data.get('is_on_notice_period') and not data.get('notice_period_end_date'):
            raise serializers.ValidationError({
                'notice_period_end_date': 'This field is required when employee is on notice period.'
            })
        
        if not data.get('is_on_notice_period') and data.get('notice_period_end_date'):
            # Clear notice_period_end_date if not on notice period
            data['notice_period_end_date'] = None
        
        return data

    def create(self, validated_data):
        create_folder = validated_data.pop('create_folder', False)
        # Handle both password and plain_password
        password = validated_data.get('password', None)
        plain_password = validated_data.get('plain_password', None)
        current_address_text = validated_data.pop('current_address_text', '')
        permanent_address_text = validated_data.pop('permanent_address_text', '')
        
        # Handle address fields
        if current_address_text:
            from common.models import Address
            current_addr = Address.objects.create(
                line1=current_address_text,
                city='N/A',  # Default value
                pincode='000000',  # Default value
                type='current'
            )
            validated_data['current_address'] = current_addr
            
        if permanent_address_text:
            from common.models import Address
            permanent_addr = Address.objects.create(
                line1=permanent_address_text,
                city='N/A',  # Default value
                pincode='000000',  # Default value
                type='permanent'
            )
            validated_data['permanent_address'] = permanent_addr
        
        # Store bank details in employee_details JSON field
        bank_details = {
            'account_holder': validated_data.pop('account_holder', ''),
            'account_number': validated_data.pop('account_number', ''),
            'ifsc_code': validated_data.pop('ifsc_code', ''),
            'branch': validated_data.pop('branch', ''),
        }
        
        # Store document link and other details
        employee_details = {
            'document_link': validated_data.pop('document_link', ''),
            'bank_details': bank_details
        }
        validated_data['employee_details'] = employee_details
        
        # Remove password from validated_data before creating the instance
        validated_data.pop('password', None)
        instance = super().create(validated_data)
        
        if password:
            instance.set_password(password)
            # Store plain password for admin viewing (if provided)
            if plain_password:
                instance.plain_password = plain_password
            instance.save()  # Save the instance after setting password
        
        # Create employee folder if requested
        if create_folder:
            folder_name = f"{instance.first_name}_{instance.last_name}_{instance.id}"
            # Create folder path relative to media root
            folder_path = os.path.join('employee_folders', folder_name)
            full_folder_path = os.path.join(settings.MEDIA_ROOT, folder_path)
            
            try:
                # Create main employee folder
                os.makedirs(full_folder_path, exist_ok=True)
                
                # Create subfolders for organization
                subfolders = ['documents', 'images', 'contracts', 'certificates']
                for subfolder in subfolders:
                    subfolder_path = os.path.join(full_folder_path, subfolder)
                    os.makedirs(subfolder_path, exist_ok=True)
                
                instance.folder_path = folder_path
                
                # Create database record for the folder
                from files.models import Folder
                main_folder = Folder.objects.create(
                    name=f"Employee_{instance.first_name}_{instance.last_name}",
                    employee=instance,
                    created_by=instance,  # or get from request context if available
                    is_employee_folder=True,
                    is_system_folder=True,
                    color='yellow',
                    description=f"Employee folder for {instance.first_name} {instance.last_name}"
                )
                
                # Create database records for subfolders
                for subfolder_name in subfolders:
                    Folder.objects.create(
                        name=subfolder_name.title(),
                        parent=main_folder,
                        employee=instance,
                        created_by=instance,
                        is_employee_folder=True,
                        is_system_folder=True,
                        color='blue',
                        description=f"{subfolder_name.title()} folder for {instance.first_name} {instance.last_name}"
                    )
                
                print(f"Successfully created folder structure for employee {instance.username} at {folder_path}")
            except Exception as e:
                # Log the error but don't fail the user creation
                print(f"Failed to create folder for employee {instance.username}: {e}")
        
        instance.save()
        return instance

    def update(self, instance, validated_data):
        create_folder = validated_data.pop('create_folder', False)
        password = validated_data.pop('password', None)
        plain_password = validated_data.pop('plain_password', None)
        current_address_text = validated_data.pop('current_address_text', '')
        permanent_address_text = validated_data.pop('permanent_address_text', '')
        
        # Handle address fields
        if current_address_text:
            from common.models import Address
            if instance.current_address:
                instance.current_address.line1 = current_address_text
                instance.current_address.save()
            else:
                current_addr = Address.objects.create(
                    line1=current_address_text,
                    city='N/A',  # Default value
                    pincode='000000',  # Default value
                    type='current'
                )
                validated_data['current_address'] = current_addr
                
        if permanent_address_text:
            from common.models import Address
            if instance.permanent_address:
                instance.permanent_address.line1 = permanent_address_text
                instance.permanent_address.save()
            else:
                permanent_addr = Address.objects.create(
                    line1=permanent_address_text,
                    city='N/A',  # Default value
                    pincode='000000',  # Default value
                    type='permanent'
                )
                validated_data['permanent_address'] = permanent_addr
        
        # Handle bank details and document link
        bank_details = {
            'account_holder': validated_data.pop('account_holder', ''),
            'account_number': validated_data.pop('account_number', ''),
            'ifsc_code': validated_data.pop('ifsc_code', ''),
            'branch': validated_data.pop('branch', ''),
        }
        
        document_link = validated_data.pop('document_link', '')
        
        # Update employee_details JSON field
        if not instance.employee_details:
            instance.employee_details = {}
        
        instance.employee_details.update({
            'document_link': document_link,
            'bank_details': bank_details
        })
        validated_data['employee_details'] = instance.employee_details
        
        instance = super().update(instance, validated_data)
        
        if password:
            instance.set_password(password)
            # Update plain password for admin viewing (if provided)
            if plain_password:
                instance.plain_password = plain_password
            instance.save()  # Save the instance after setting password
        
        # Create employee folder if requested and not already created
        if create_folder and not instance.folder_path:
            folder_name = f"{instance.first_name}_{instance.last_name}_{instance.id}"
            folder_path = os.path.join('employee_folders', folder_name)
            full_folder_path = os.path.join(settings.MEDIA_ROOT, folder_path)
            
            try:
                # Create main employee folder
                os.makedirs(full_folder_path, exist_ok=True)
                
                # Create subfolders for organization
                subfolders = ['documents', 'images', 'contracts', 'certificates']
                for subfolder in subfolders:
                    subfolder_path = os.path.join(full_folder_path, subfolder)
                    os.makedirs(subfolder_path, exist_ok=True)
                
                instance.folder_path = folder_path
                
                # Create database record for the folder
                from files.models import Folder
                main_folder = Folder.objects.create(
                    name=f"Employee_{instance.first_name}_{instance.last_name}",
                    employee=instance,
                    created_by=instance,
                    is_employee_folder=True,
                    is_system_folder=True,
                    color='yellow',
                    description=f"Employee folder for {instance.first_name} {instance.last_name}"
                )
                
                # Create database records for subfolders
                for subfolder_name in subfolders:
                    Folder.objects.create(
                        name=subfolder_name.title(),
                        parent=main_folder,
                        employee=instance,
                        created_by=instance,
                        is_employee_folder=True,
                        is_system_folder=True,
                        color='blue',
                        description=f"{subfolder_name.title()} folder for {instance.first_name} {instance.last_name}"
                    )
                
                print(f"Successfully created folder structure for employee {instance.username} at {folder_path}")
            except Exception as e:
                print(f"Failed to create folder for employee {instance.username}: {e}")
        
        instance.save()
        return instance


class ProfileUpdateRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True)
    
    class Meta:
        model = ProfileUpdateRequest
        fields = [
            'id', 'user', 'user_name', 'user_email', 'field_name', 
            'old_value', 'new_value', 'status', 'reason', 'admin_comment',
            'approved_by', 'approved_by_name', 'requested_at', 'processed_at'
        ]
        read_only_fields = ['user', 'requested_at', 'processed_at', 'approved_by']

class ProfileUpdateRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileUpdateRequest
        fields = ['field_name', 'old_value', 'new_value', 'reason']
    
    def create(self, validated_data):
        # Get user from request context
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)


class EmployeePaymentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.username', read_only=True)
    employee_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = EmployeePayment
        fields = [
            'id', 'employee', 'employee_name', 'employee_full_name', 
            'payment_type', 'amount', 'amount_per_hour', 'working_hours', 
            'date', 'description', 'created_at', 'updated_at'
        ]
        read_only_fields = ['employee', 'created_at', 'updated_at']
    
    def get_employee_full_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"
    
    def validate(self, data):
        payment_type = data.get('payment_type')
        
        if payment_type == 'hourly':
            if not data.get('amount_per_hour') or not data.get('working_hours'):
                raise serializers.ValidationError(
                    "Amount per hour and working hours are required for hourly payments"
                )
            # Calculate total amount for hourly payments
            data['amount'] = data['amount_per_hour'] * data['working_hours']
        elif payment_type == 'fixed':
            if not data.get('amount'):
                raise serializers.ValidationError(
                    "Amount is required for fixed payments"
                )
            # Clear hourly fields for fixed payments
            data['amount_per_hour'] = None
            data['working_hours'] = None
        
        return data
