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

