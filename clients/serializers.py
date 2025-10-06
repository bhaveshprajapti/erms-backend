from rest_framework import serializers
from .models import Client, ClientRole, Quotation

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'

class ClientRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientRole
        fields = '__all__'

class QuotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quotation
        fields = '__all__'
