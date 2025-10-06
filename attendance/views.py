from rest_framework import viewsets
from .models import Attendance, LeaveRequest, TimeAdjustment, Approval
from .serializers import (
    AttendanceSerializer, LeaveRequestSerializer, 
    TimeAdjustmentSerializer, ApprovalSerializer
)

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer

class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer

class TimeAdjustmentViewSet(viewsets.ModelViewSet):
    queryset = TimeAdjustment.objects.all()
    serializer_class = TimeAdjustmentSerializer

class ApprovalViewSet(viewsets.ModelViewSet):
    queryset = Approval.objects.all()
    serializer_class = ApprovalSerializer

