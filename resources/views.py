from rest_framework import viewsets
from .models import Equipment, Inventory, ResourceAllocation
from .serializers import (
    EquipmentSerializer, InventorySerializer, ResourceAllocationSerializer
)

class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipment.objects.all().order_by('-created_at')
    serializer_class = EquipmentSerializer

class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all().order_by('-created_at')
    serializer_class = InventorySerializer

class ResourceAllocationViewSet(viewsets.ModelViewSet):
    queryset = ResourceAllocation.objects.all().order_by('-created_at')
    serializer_class = ResourceAllocationSerializer

