from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, time, timedelta
from common.models import StatusChoice
from .models import Attendance, LeaveRequest, TimeAdjustment, Approval
from .serializers import (
    AttendanceSerializer, LeaveRequestSerializer, 
    TimeAdjustmentSerializer, ApprovalSerializer
)

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Attendance.objects.all()
        if not (user.is_staff or user.is_superuser):
            qs = qs.filter(user=user)
        # Optional filters for staff/admin
        user_id = self.request.query_params.get('user')
        if user_id and (user.is_staff or user.is_superuser):
            qs = qs.filter(user_id=user_id)
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        return qs

    def create(self, request, *args, **kwargs):
        # Allow employees to create their own attendance records via check-in/out actions
        # Only restrict direct creation via admin
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Use check-in/check-out actions for attendance.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Only staff can update attendance records.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Only staff can delete attendance records.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    def _check_leave_status(self, user, date):
        """Check if user is on approved leave for the given date"""
        try:
            approved_status = StatusChoice.objects.get(category='leave_status', name__iexact='Approved')
            return LeaveRequest.objects.filter(
                user=user,
                start_date__lte=date,
                end_date__gte=date,
                status=approved_status
            ).exists()
        except StatusChoice.DoesNotExist:
            return False

    def _get_user_shifts(self, user):
        """Get user's active shifts"""
        return user.shifts.filter(is_active=True)

    def _is_within_shift_hours(self, current_time, shifts, allow_overtime=False):
        """Check if current time is within any of the user's shift hours"""
        current_time_only = current_time.time()
        
        for shift in shifts:
            start_time = shift.start_time
            end_time = shift.end_time
            
            if shift.is_overnight:
                # For overnight shifts, check if time is after start OR before end
                if current_time_only >= start_time or current_time_only <= end_time:
                    return True
            else:
                # For regular shifts
                if allow_overtime:
                    # Allow check-out up to 4 hours after shift end for overtime
                    extended_end = (datetime.combine(datetime.today(), end_time) + timedelta(hours=4)).time()
                    if start_time <= current_time_only <= extended_end:
                        return True
                else:
                    if start_time <= current_time_only <= end_time:
                        return True
        return False

    def _calculate_total_hours(self, sessions):
        """Calculate total working hours from sessions"""
        total_seconds = 0
        for session in sessions:
            if 'check_in' in session and 'check_out' in session:
                check_in = datetime.fromisoformat(session['check_in'])
                check_out = datetime.fromisoformat(session['check_out'])
                duration = check_out - check_in
                total_seconds += duration.total_seconds()
        
        return timedelta(seconds=total_seconds)

    def _calculate_break_time(self, sessions):
        """Calculate total break time between sessions"""
        if len(sessions) < 2:
            return timedelta(0)
        
        total_break_seconds = 0
        for i in range(1, len(sessions)):
            prev_session = sessions[i-1]
            curr_session = sessions[i]
            
            if 'check_out' in prev_session and 'check_in' in curr_session:
                prev_checkout = datetime.fromisoformat(prev_session['check_out'])
                curr_checkin = datetime.fromisoformat(curr_session['check_in'])
                break_duration = curr_checkin - prev_checkout
                total_break_seconds += break_duration.total_seconds()
        
        return timedelta(seconds=total_break_seconds)

    @action(detail=False, methods=['post'])
    def check_in(self, request):
        """Check-in action for employees"""
        user = request.user
        now = timezone.now()
        today = now.date()
        
        # Check if user is on leave
        if self._check_leave_status(user, today):
            return Response({
                'detail': 'Cannot check-in while on approved leave.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user shifts
        shifts = self._get_user_shifts(user)
        if not shifts.exists():
            return Response({
                'detail': 'No shift assigned. Contact admin.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if within shift hours
        if not self._is_within_shift_hours(now, shifts):
            return Response({
                'detail': 'Check-in not allowed outside shift hours.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create attendance record for today
        attendance, created = Attendance.objects.get_or_create(
            user=user,
            date=today,
            defaults={'sessions': []}
        )
        
        sessions = attendance.sessions or []
        
        # Check if user is already checked in (last session has no check_out)
        if sessions and 'check_out' not in sessions[-1]:
            return Response({
                'detail': 'Already checked in. Please check out first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Add new session
        location = request.data.get('location', {})
        new_session = {
            'check_in': now.isoformat(),
            'location_in': location
        }
        sessions.append(new_session)
        
        attendance.sessions = sessions
        attendance.save()
        
        return Response({
            'message': 'Checked in successfully',
            'check_in_time': now.isoformat(),
            'session_count': len(sessions)
        })

    @action(detail=False, methods=['post'])
    def check_out(self, request):
        """Check-out action for employees"""
        user = request.user
        now = timezone.now()
        today = now.date()
        
        try:
            attendance = Attendance.objects.get(user=user, date=today)
        except Attendance.DoesNotExist:
            return Response({
                'detail': 'No check-in found for today. Please check in first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        sessions = attendance.sessions or []
        if not sessions or 'check_out' in sessions[-1]:
            return Response({
                'detail': 'Not currently checked in. Please check in first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user shifts for overtime validation
        shifts = self._get_user_shifts(user)
        
        # Allow check-out even outside shift hours (for overtime)
        location = request.data.get('location', {})
        sessions[-1]['check_out'] = now.isoformat()
        sessions[-1]['location_out'] = location
        
        # Calculate totals
        attendance.sessions = sessions
        attendance.total_hours = self._calculate_total_hours(sessions)
        attendance.save()
        
        break_time = self._calculate_break_time(sessions)
        
        return Response({
            'message': 'Checked out successfully',
            'check_out_time': now.isoformat(),
            'session_count': len(sessions),
            'total_hours': str(attendance.total_hours),
            'break_time': str(break_time)
        })

    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get current attendance status for the user"""
        user = request.user
        today = timezone.now().date()
        
        try:
            attendance = Attendance.objects.get(user=user, date=today)
            sessions = attendance.sessions or []
            
            is_checked_in = sessions and 'check_out' not in sessions[-1]
            total_sessions = len(sessions)
            completed_sessions = len([s for s in sessions if 'check_out' in s])
            
            response_data = {
                'date': today,
                'is_checked_in': is_checked_in,
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'total_hours': str(attendance.total_hours) if attendance.total_hours else '0:00:00',
            }
            
            if sessions:
                response_data['last_check_in'] = sessions[-1].get('check_in')
                response_data['last_check_out'] = sessions[-1].get('check_out')
                response_data['break_time'] = str(self._calculate_break_time(sessions))
            
            # Check if on leave
            response_data['is_on_leave'] = self._check_leave_status(user, today)
            
            return Response(response_data)
            
        except Attendance.DoesNotExist:
            return Response({
                'date': today,
                'is_checked_in': False,
                'total_sessions': 0,
                'completed_sessions': 0,
                'total_hours': '0:00:00',
                'break_time': '0:00:00',
                'is_on_leave': self._check_leave_status(user, today)
            })

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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = TimeAdjustment.objects.all()
        if not (user.is_staff or user.is_superuser):
            qs = qs.filter(user=user)
        # Optional filters for staff/admin
        user_id = self.request.query_params.get('user')
        if user_id and (user.is_staff or user.is_superuser):
            qs = qs.filter(user_id=user_id)
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        status_id = self.request.query_params.get('status')
        if status_id:
            qs = qs.filter(status_id=status_id)
        return qs

    def create(self, request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Only staff can create time adjustments via admin.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Only staff can update time adjustments.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Only staff can delete time adjustments.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

class ApprovalViewSet(viewsets.ModelViewSet):
    queryset = Approval.objects.all()
    serializer_class = ApprovalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Approval.objects.all()
        # Non-staff can only view approvals where they are the approver
        return Approval.objects.filter(approver=user)

