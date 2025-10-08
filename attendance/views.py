from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from common.models import StatusChoice
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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = LeaveRequest.objects.all()

        # Non-staff users can only see their own requests
        if not (user.is_staff or user.is_superuser):
            queryset = queryset.filter(user=user)

        # Optional filters
        status_name = self.request.query_params.get('status')
        if status_name:
            queryset = queryset.filter(status__name__iexact=status_name)

        user_id = self.request.query_params.get('user')
        if user_id and (user.is_staff or user.is_superuser):
            queryset = queryset.filter(user_id=user_id)

        org_id = self.request.query_params.get('organization')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(reason__icontains=search)
                | Q(leave_type__name__icontains=search)
            )
        return queryset.order_by('-created_at')

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        """Approve a leave request (admin/staff only)."""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        leave_request = self.get_object()

        # Determine pending/approved statuses
        try:
            approved_status = StatusChoice.objects.get(category='leave_status', name__iexact='Approved')
            pending_status = StatusChoice.objects.get(category='leave_status', name__iexact='Pending')
        except StatusChoice.DoesNotExist:
            return Response(
                {'detail': 'Required leave statuses (Pending/Approved) are not configured.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if leave_request.status and leave_request.status.name.lower() != 'pending':
            return Response({'detail': 'Only pending requests can be approved.'}, status=status.HTTP_400_BAD_REQUEST)

        # If status is None, treat as pending
        if leave_request.status is None or leave_request.status_id == pending_status.id:
            leave_request.status = approved_status
            leave_request.approver = request.user
            leave_request.rejection_reason = None
            leave_request.save()
            return Response({'message': 'Leave request approved.'})

        return Response({'detail': 'Invalid request state.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        """Reject a leave request (admin/staff only)."""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        leave_request = self.get_object()
        reason = request.data.get('reason', '')

        # Determine pending/rejected statuses
        try:
            rejected_status = StatusChoice.objects.get(category='leave_status', name__iexact='Rejected')
            pending_status = StatusChoice.objects.get(category='leave_status', name__iexact='Pending')
        except StatusChoice.DoesNotExist:
            return Response(
                {'detail': 'Required leave statuses (Pending/Rejected) are not configured.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if leave_request.status and leave_request.status.name.lower() != 'pending':
            return Response({'detail': 'Only pending requests can be rejected.'}, status=status.HTTP_400_BAD_REQUEST)

        # If status is None, treat as pending
        if leave_request.status is None or leave_request.status_id == pending_status.id:
            leave_request.status = rejected_status
            leave_request.approver = request.user
            leave_request.rejection_reason = reason
            leave_request.save()
            return Response({'message': 'Leave request rejected.'})

        return Response({'detail': 'Invalid request state.'}, status=status.HTTP_400_BAD_REQUEST)

class TimeAdjustmentViewSet(viewsets.ModelViewSet):
    queryset = TimeAdjustment.objects.all()
    serializer_class = TimeAdjustmentSerializer

class ApprovalViewSet(viewsets.ModelViewSet):
    queryset = Approval.objects.all()
    serializer_class = ApprovalSerializer

