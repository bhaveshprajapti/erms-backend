from rest_framework import serializers
from .models import Attendance, LeaveRequest, TimeAdjustment, Approval

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'

class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = '__all__'

class TimeAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeAdjustment
        fields = '__all__'

class ApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Approval
        fields = '__all__'
