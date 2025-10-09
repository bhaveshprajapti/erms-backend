from rest_framework import viewsets
from .models import (
    LeaveType, LeavePolicy, LeaveBalance, 
    FlexAllowanceType, FlexPolicy, FlexBalance
)
from .serializers import (
    LeaveTypeSerializer, LeavePolicySerializer, LeaveBalanceSerializer,
    FlexAllowanceTypeSerializer, FlexPolicySerializer, FlexBalanceSerializer
)

class LeaveTypeViewSet(viewsets.ModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer

    def perform_destroy(self, instance):
        # Prevent deleting a leave type that is used in any policy
        if LeavePolicy.objects.filter(leave_types=instance).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                'detail': f'Cannot delete leave type "{instance.name}" because it is used in one or more leave policies.'
            })
        super().perform_destroy(instance)

class LeavePolicyViewSet(viewsets.ModelViewSet):
    queryset = LeavePolicy.objects.all()
    serializer_class = LeavePolicySerializer

class LeaveBalanceViewSet(viewsets.ModelViewSet):
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer

class FlexAllowanceTypeViewSet(viewsets.ModelViewSet):
    queryset = FlexAllowanceType.objects.all()
    serializer_class = FlexAllowanceTypeSerializer

class FlexPolicyViewSet(viewsets.ModelViewSet):
    queryset = FlexPolicy.objects.all()
    serializer_class = FlexPolicySerializer

class FlexBalanceViewSet(viewsets.ModelViewSet):
    queryset = FlexBalance.objects.all()
    serializer_class = FlexBalanceSerializer
    serializer_class = FlexBalanceSerializer

