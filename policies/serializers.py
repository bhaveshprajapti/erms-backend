from rest_framework import serializers
from .models import (
    LeaveType, LeavePolicy, LeaveBalance, 
    FlexAllowanceType, FlexPolicy, FlexBalance
)

class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = '__all__'

class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = '__all__'

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = '__all__'

class FlexAllowanceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlexAllowanceType
        fields = '__all__'

class FlexPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = FlexPolicy
        fields = '__all__'

class FlexBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlexBalance
        fields = '__all__'
