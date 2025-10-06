from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LeaveTypeViewSet, LeavePolicyViewSet, LeaveBalanceViewSet,
    FlexAllowanceTypeViewSet, FlexPolicyViewSet, FlexBalanceViewSet
)

router = DefaultRouter()
router.register(r'leave-types', LeaveTypeViewSet)
router.register(r'leave-policies', LeavePolicyViewSet)
router.register(r'leave-balances', LeaveBalanceViewSet)
router.register(r'flex-allowance-types', FlexAllowanceTypeViewSet)
router.register(r'flex-policies', FlexPolicyViewSet)
router.register(r'flex-balances', FlexBalanceViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
