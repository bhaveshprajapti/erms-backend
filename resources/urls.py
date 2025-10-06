from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EquipmentViewSet, InventoryViewSet, ResourceAllocationViewSet

router = DefaultRouter()
router.register(r'equipment', EquipmentViewSet)
router.register(r'inventory', InventoryViewSet)
router.register(r'resource-allocations', ResourceAllocationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
