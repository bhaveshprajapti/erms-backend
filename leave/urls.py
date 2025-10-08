from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeaveRequestViewSet, LeaveBalanceViewSet

router = DefaultRouter()
router.register(r'leave-requests', LeaveRequestViewSet)
router.register(r'leave-balances', LeaveBalanceViewSet)

urlpatterns = [
    path('', include(router.urls)),
]