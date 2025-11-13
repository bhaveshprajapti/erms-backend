from rest_framework import serializers
from .models import Client, ClientRole, Quotation


class ClientListSerializer(serializers.ModelSerializer):
    """Simplified serializer for client list/dropdown"""
    address_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone', 'gst_number', 'website', 'rating', 'is_active', 'address_info', 'created_at']
    
    def get_address_info(self, obj):
        """Get formatted address information"""
        if obj.address:
            parts = []
            if obj.address.line1:
                parts.append(obj.address.line1)
            if obj.address.line2:
                parts.append(obj.address.line2)
            if obj.address.city:
                parts.append(obj.address.city)
            if obj.address.state:
                parts.append(obj.address.state)
            if obj.address.country:
                parts.append(obj.address.country)
            return ', '.join(parts) if parts else None
        return None


class ClientSerializer(serializers.ModelSerializer):
    """Full client serializer for CRUD operations"""
    # Address fields for nested handling
    address_line1 = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address_line2 = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address_country = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address_state = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address_city = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address_pincode = serializers.CharField(write_only=True, required=False, allow_blank=True)
    company_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    # Read-only address info for display
    address_info = serializers.SerializerMethodField(read_only=True)
    
    # Read-only address fields for editing
    address_details = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Client
        fields = [
            'id', 'name', 'email', 'phone', 'organization', 'address', 'status',
            'rating', 'gst_number', 'website', 'is_active', 'created_at',
            # Write-only fields for form handling
            'address_line1', 'address_line2', 'address_country', 
            'address_state', 'address_city', 'address_pincode', 'company_name',
            # Read-only computed fields
            'address_info', 'address_details'
        ]
        extra_kwargs = {
            'organization': {'required': False},
            'address': {'required': False, 'read_only': True},
            'status': {'required': False},
            'created_at': {'read_only': True},
        }
    
    def get_address_info(self, obj):
        """Get formatted address information"""
        if obj.address:
            parts = []
            if obj.address.line1:
                parts.append(obj.address.line1)
            if obj.address.line2:
                parts.append(obj.address.line2)
            if obj.address.city:
                parts.append(obj.address.city)
            if obj.address.state:
                parts.append(obj.address.state)
            if obj.address.country:
                parts.append(obj.address.country)
            return ', '.join(parts) if parts else None
        return None
    
    def get_address_details(self, obj):
        """Get individual address fields for form editing"""
        if obj.address:
            return {
                'line1': obj.address.line1 or '',
                'line2': obj.address.line2 or '',
                'city': obj.address.city or '',
                'state': obj.address.state or '',
                'country': obj.address.country or '',
                'pincode': obj.address.pincode or ''
            }
        return {
            'line1': '',
            'line2': '',
            'city': '',
            'state': '',
            'country': 'India',
            'pincode': ''
        }
    
    def create(self, validated_data):
        # Extract address and company fields
        address_data = {
            'line1': validated_data.pop('address_line1', ''),
            'line2': validated_data.pop('address_line2', ''),
            'country': validated_data.pop('address_country', 'India'),
            'state': validated_data.pop('address_state', ''),
            'city': validated_data.pop('address_city', ''),
            'pincode': validated_data.pop('address_pincode', ''),
            'type': 'current',
            'is_primary': True
        }
        
        # Remove company_name as it's just for form display (can be stored in name field)
        company_name = validated_data.pop('company_name', None)
        
        # Create address if any address data provided
        address = None
        if any(address_data[key] for key in ['line1', 'city', 'state', 'pincode']):
            from common.models import Address
            address = Address.objects.create(**address_data)
        
        # Create client
        client = Client.objects.create(
            address=address,
            **validated_data
        )
        
        return client
    
    def update(self, instance, validated_data):
        # Extract address fields
        address_data = {
            'line1': validated_data.pop('address_line1', None),
            'line2': validated_data.pop('address_line2', None),
            'country': validated_data.pop('address_country', None),
            'state': validated_data.pop('address_state', None),
            'city': validated_data.pop('address_city', None),
            'pincode': validated_data.pop('address_pincode', None),
        }
        
        # Remove company_name
        company_name = validated_data.pop('company_name', None)
        
        # Update or create address
        if any(v is not None for v in address_data.values()):
            from common.models import Address
            
            if instance.address:
                # Update existing address
                for key, value in address_data.items():
                    if value is not None:
                        setattr(instance.address, key, value)
                instance.address.save()
            else:
                # Create new address
                clean_address_data = {k: v for k, v in address_data.items() if v is not None}
                if clean_address_data:
                    clean_address_data.update({
                        'type': 'current',
                        'is_primary': True,
                        'country': clean_address_data.get('country', 'India')
                    })
                    address = Address.objects.create(**clean_address_data)
                    instance.address = address
        
        # Update other client fields
        for key, value in validated_data.items():
            setattr(instance, key, value)
        
        instance.save()
        return instance


class ClientRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientRole
        fields = '__all__'


class QuotationSerializer(serializers.ModelSerializer):
    """Full quotation serializer with calculated fields"""
    client_info = serializers.SerializerMethodField()
    quotation_no = serializers.CharField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    grand_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_no', 'client', 'client_info',
            'client_name', 'client_email', 'client_phone', 'client_address',
            'title', 'description', 'notes', 'terms_conditions',
            'prepared_by', 'lead_source',
            'date', 'valid_until',
            'service_items', 'domain_registration', 'server_hosting', 'ssl_certificate', 'email_hosting',
            'line_items', 'subtotal', 'tax_rate', 'tax_amount', 
            'discount_type', 'discount_value', 'discount', 'total_amount', 'grand_total',
            'payment_terms', 'additional_notes', 'signatory_name', 'signatory_designation', 'signature',
            'status', 'is_converted', 'converted_project',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'date': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }
    
    def get_client_info(self, obj):
        """Get client information from linked client or stored fields"""
        return obj.get_client_info()
    
    def create(self, validated_data):
        """Create quotation and calculate totals"""
        quotation = super().create(validated_data)
        quotation.calculate_totals()
        quotation.save()
        return quotation
    
    def update(self, instance, validated_data):
        """Update quotation and recalculate totals"""
        quotation = super().update(instance, validated_data)
        quotation.calculate_totals()
        quotation.save()
        return quotation
    
    def validate(self, data):
        """Validate that either client is linked or client info is provided"""
        client = data.get('client')
        client_name = data.get('client_name')
        
        if not client and not client_name:
            raise serializers.ValidationError(
                "Either select a client or provide client name for standalone quotation."
            )
        
        return data


class QuotationListSerializer(serializers.ModelSerializer):
    """Simplified serializer for quotation list view"""
    client_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_no', 'client_info', 'title', 'date',
            'total_amount', 'status', 'is_converted', 'valid_until', 'created_at', 'updated_at'
        ]
    
    def get_client_info(self, obj):
        return obj.get_client_info()
