from rest_framework import serializers
from .models import Equipment, Inventory, ResourceAllocation

class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = '__all__'

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = '__all__'

class ResourceAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceAllocation
        fields = '__all__'
