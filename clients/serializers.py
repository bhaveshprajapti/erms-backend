from rest_framework import serializers
from .models import Client, ClientRole, Quotation


class ClientListSerializer(serializers.ModelSerializer):
    """Simplified serializer for client list/dropdown"""
    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone']


class ClientSerializer(serializers.ModelSerializer):
    """Full client serializer for CRUD operations"""
    class Meta:
        model = Client
        fields = '__all__'


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
    
    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_no', 'client', 'client_info',
            'client_name', 'client_email', 'client_phone', 'client_address',
            'title', 'description', 'notes', 'terms_conditions',
            'date', 'valid_until',
            'line_items', 'subtotal', 'tax_rate', 'tax_amount', 'discount', 'total_amount',
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
            'id', 'quotation_no', 'client_info', 'title', 
            'total_amount', 'status', 'is_converted', 'valid_until', 'created_at'
        ]
    
    def get_client_info(self, obj):
        return obj.get_client_info()
