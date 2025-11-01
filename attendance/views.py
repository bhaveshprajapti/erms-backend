from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from common.models import StatusChoice
from common.timezone_utils import get_ist_time, get_ist_date, get_current_ist_date, format_time_12hour
from .models import Attendance, LeaveRequest, TimeAdjustment, Approval, SessionLog
from leave.models import FlexibleTimingRequest
from .serializers import (
    AttendanceSerializer, LeaveRequestSerializer, 
    TimeAdjustmentSerializer, ApprovalSerializer
)

# IST utilities moved to common.timezone_utils

def format_duration(duration):
    """Format timedelta to HH:MM:SS format"""
    if not duration:
        return '0:00:00'
    
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    return f"{hours}:{minutes:02d}:{seconds:02d}"

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all().order_by('-date', '-created_at')
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
        return qs.order_by('-date', '-created_at')

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

    def _check_leave_status(self, user, date, current_time=None):
        """Check if user is on approved leave for the given date and time"""
        try:
            from leave.models import LeaveApplication
            
            # Filter for approved leaves (status = 'approved')
            leave_applications = LeaveApplication.objects.filter(
                user=user,
                start_date__lte=date,
                end_date__gte=date,
                status='approved'  # Only check approved leaves
            )
            
            for leave in leave_applications:
                # For full-day leave, block completely
                if not leave.is_half_day:
                    return True, f"You are on approved {leave.leave_type.name} leave today. Check-in is not allowed. Contact admin if you need to work."
                
                # For half-day leave, check timing using IST
                if current_time and leave.is_half_day and leave.half_day_period:
                    ist_time = get_ist_time(current_time)
                    current_hour = ist_time.hour
                    
                    if leave.half_day_period == 'morning':
                        # Morning half-day leave (before 1 PM IST)
                        if current_hour < 13:
                            return True, f"You are on approved morning half-day {leave.leave_type.name} leave. Check-in allowed after 1:00 PM IST."
                    elif leave.half_day_period == 'afternoon':
                        # Afternoon half-day leave (after 1 PM IST)
                        if current_hour >= 13:
                            return True, f"You are on approved afternoon half-day {leave.leave_type.name} leave. Check-in allowed before 1:00 PM IST."
            
            return False, ""
        except Exception as e:
            # If there's any error, allow check-in (fail open)
            print(f"Error checking leave status: {e}")
            return False, ""

    def _check_flexible_timing_status(self, user, date, current_time):
        """Check if user has approved flexible timing for the given date and time"""
        try:
            approved_status = StatusChoice.objects.get(category='flexible_timing_status', name__iexact='Approved')
            flexible_requests = FlexibleTimingRequest.objects.filter(
                user=user,
                requested_date=date,
                status=approved_status
            )
            
            for request in flexible_requests:
                current_hour = current_time.hour
                current_minute = current_time.minute
                current_total_minutes = current_hour * 60 + current_minute
                
                # Check if current time falls within the flexible timing period
                if hasattr(request, 'start_time') and hasattr(request, 'end_time') and request.start_time and request.end_time:
                    start_minutes = request.start_time.hour * 60 + request.start_time.minute
                    end_minutes = request.end_time.hour * 60 + request.end_time.minute
                    
                    if start_minutes <= current_total_minutes <= end_minutes:
                        return True, f"You have approved flexible timing from {request.start_time} to {request.end_time}. Check-in allowed during this period."
            
            return False, ""
        except (StatusChoice.DoesNotExist, AttributeError):
            return False, ""

    def _get_user_shifts(self, user):
        """Get user's active shifts"""
        return user.shifts.filter(is_active=True)

    def _is_within_shift_hours(self, current_time, shifts, allow_overtime=False, check_in_grace=False):
        """Check if current time is within any of the user's shift hours"""
        # Convert UTC time to IST (India Standard Time - UTC+5:30)
        ist_tz = ZoneInfo('Asia/Kolkata')
        current_time_ist = current_time.astimezone(ist_tz)
        current_time_only = current_time_ist.time()
        
        for shift in shifts:
            start_time = shift.start_time
            end_time = shift.end_time
            
            # Detect overnight shift ONLY by comparing times, ignore the flag
            is_overnight = end_time < start_time
            
            if is_overnight:
                # For overnight shifts, check if time is after start OR before end
                if current_time_only >= start_time or current_time_only <= end_time:
                    return True
            else:
                # For regular shifts (start_time <= end_time)
                if check_in_grace:
                    # Allow check-in 3 hours before shift start (e.g., 7 AM for 10 AM shift)
                    early_start = (datetime.combine(datetime.today(), start_time) - timedelta(hours=3)).time()
                    # Allow check-in up to 15 minutes after shift start (e.g., 10:15 AM for 10 AM shift)
                    grace_end = (datetime.combine(datetime.today(), start_time) + timedelta(minutes=15)).time()
                    
                    if early_start <= current_time_only <= grace_end:
                        return True
                        
                elif allow_overtime:
                    # Allow check-out up to 4 hours after shift end for overtime
                    extended_end = (datetime.combine(datetime.today(), end_time) + timedelta(hours=4)).time()
                    if start_time <= current_time_only <= extended_end:
                        return True
                else:
                    if start_time <= current_time_only <= end_time:
                        return True
        return False

    def _calculate_total_hours(self, sessions):
        """Calculate total working hours from completed sessions only"""
        total_seconds = 0
        for session in sessions:
            if 'check_in' in session and 'check_out' in session:
                check_in = datetime.fromisoformat(session['check_in'])
                check_out = datetime.fromisoformat(session['check_out'])
                duration = check_out - check_in
                total_seconds += duration.total_seconds()
        
        return timedelta(seconds=total_seconds)
    
    def _calculate_realtime_total_hours(self, sessions, current_time, break_start_time=None):
        """Calculate total working hours including current active session, excluding break time"""
        total_seconds = 0
        
        # Ensure current_time is timezone-aware
        if current_time.tzinfo is None:
            current_time = timezone.make_aware(current_time)
        
        for session in sessions:
            if 'check_in' in session:
                check_in = datetime.fromisoformat(session['check_in'])
                # Ensure check_in is timezone-aware
                if check_in.tzinfo is None:
                    check_in = timezone.make_aware(check_in)
                
                if 'check_out' in session:
                    # Completed session
                    check_out = datetime.fromisoformat(session['check_out'])
                    if check_out.tzinfo is None:
                        check_out = timezone.make_aware(check_out)
                    duration = check_out - check_in
                    total_seconds += duration.total_seconds()
                else:
                    # Active session - calculate up to current time, excluding break time
                    if break_start_time:
                        # Ensure break_start_time is timezone-aware
                        if break_start_time.tzinfo is None:
                            break_start_time = timezone.make_aware(break_start_time)
                        # If on break, count only up to break start
                        duration = break_start_time - check_in
                    else:
                        # If not on break, count up to current time
                        duration = current_time - check_in
                    
                    if duration.total_seconds() > 0:
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

    def _cleanup_previous_active_sessions(self, user, current_date, request):
        """
        Automatically cleanup any previous day's active sessions by calling existing methods.
        This handles cases where users forgot to check out or end their day.
        """
        try:
            # Find all attendance records for this user that are not from today and not ended
            previous_attendances = Attendance.objects.filter(
                user=user,
                date__lt=current_date
            ).exclude(
                day_ended=True  # Skip already ended days
            )
            
            cleanup_count = 0
            for attendance in previous_attendances:
                sessions = attendance.sessions or []
                if not sessions:
                    continue
                
                # Check if there's an active session or user is on break
                has_active_session = sessions and 'check_out' not in sessions[-1]
                is_on_break = hasattr(attendance, 'break_start_time') and attendance.break_start_time
                
                if has_active_session or is_on_break:
                    cleanup_count += 1
                    
                    # Create a mock request for the cleanup operations
                    from django.http import HttpRequest
                    mock_request = HttpRequest()
                    mock_request.user = user
                    mock_request.method = 'POST'
                    mock_request.data = {'location': {}}  # Empty location for cleanup
                    
                    # Temporarily override the date context by modifying the attendance date check
                    # We'll call the existing methods which will operate on the attendance record
                    
                    # Step 1: If user is on break, end the break first
                    if is_on_break:
                        # Call the existing end_break method logic directly
                        # Calculate break duration and add to total break time
                        break_duration = timezone.now() - attendance.break_start_time
                        if attendance.total_break_time is None:
                            attendance.total_break_time = break_duration
                        else:
                            attendance.total_break_time += break_duration
                        
                        # Start new session to end the break
                        new_session = {
                            'check_in': timezone.now().isoformat(),
                            'location_in': {}
                        }
                        sessions.append(new_session)
                        attendance.sessions = sessions
                        attendance.break_start_time = None
                        attendance.total_hours = self._calculate_total_hours([s for s in sessions if 'check_out' in s])
                        attendance.save()
                    
                    # Step 2: If there's still an active session, end it (end of day)
                    if sessions and 'check_out' not in sessions[-1]:
                        # Close the current session
                        sessions[-1]['check_out'] = timezone.now().isoformat()
                        sessions[-1]['location_out'] = {}
                        
                        # Calculate final totals and mark day as ended
                        attendance.sessions = sessions
                        attendance.total_hours = self._calculate_total_hours(sessions)
                        attendance.day_ended = True
                        attendance.day_end_time = timezone.now()
                        
                        # Calculate day status
                        day_status = self._calculate_day_status(attendance.total_hours, user)
                        attendance.day_status = day_status
                        
                        attendance.save()
                    
                    # Log the cleanup action
                    try:
                        SessionLog.log_event(
                            user=user,
                            event_type='auto_cleanup',
                            date=attendance.date,
                            session_count=len(sessions),
                            notes=f'Automatic cleanup of previous day session. Day status: {getattr(attendance, "day_status", "Unknown")}',
                            request=None
                        )
                    except Exception as e:
                        print(f"Failed to log auto cleanup event: {e}")
            
            return cleanup_count
            
        except Exception as e:
            print(f"Error during previous session cleanup: {e}")
            return 0

    @action(detail=False, methods=['post'])
    def check_in(self, request):
        """Check-in action for employees with session logging and timeout validation"""
        user = request.user
        now = timezone.now()  # Store UTC
        today = get_ist_date(now)  # Use IST date for business logic
        
        # CRITICAL: Check for expired sessions (with backward compatibility)
        try:
            SessionLog.check_and_handle_expired_sessions()
            
            # Validate active session - user must have logged in within timeout period
            active_session = SessionLog.get_active_session(user)
            if active_session and active_session.is_session_expired():
                return Response({
                    'detail': 'Session expired or not found. Please log in again to continue.',
                    'session_expired': True
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Update session activity
            if active_session:
                active_session.update_activity()
        except Exception as e:
            # SessionLog table might not exist yet - continue without session management
            print(f"Session management not available in check_in: {e}")
            active_session = None
        
        # AUTOMATIC CLEANUP: Handle any previous day's active sessions silently
        # This runs in the background before allowing new check-in
        cleanup_count = self._cleanup_previous_active_sessions(user, today, request)
        if cleanup_count > 0:
            print(f"Auto-cleaned {cleanup_count} previous active session(s) for user {user.username}")
        
        # Check if user is on leave
        is_on_leave, leave_message = self._check_leave_status(user, today, now)
        if is_on_leave:
            return Response({
                'detail': leave_message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user shifts
        shifts = self._get_user_shifts(user)
        if not shifts.exists():
            return Response({
                'detail': 'No shift assigned. Contact admin.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create attendance record for today to check if this is first check-in
        attendance, created = Attendance.objects.get_or_create(
            user=user,
            date=today,
            defaults={'sessions': []}
        )
        
        sessions = attendance.sessions or []
        is_first_checkin = len(sessions) == 0
        
        # Check if admin has reset the day TODAY and this is the first check-in after reset
        admin_reset_override = False
        if (is_first_checkin and 
            hasattr(attendance, 'admin_reset_at') and 
            attendance.admin_reset_at is not None):
            # Check if the reset was done today (same IST date)
            reset_date = get_ist_date(attendance.admin_reset_at)
            if reset_date == today:
                admin_reset_override = True
        
        # Apply different validation based on check-in type
        if is_first_checkin:
            # First check-in of the day - apply strict shift validation unless admin reset
            if not admin_reset_override:
                shift_result = self._is_within_shift_hours(now, shifts, check_in_grace=True)
                within_shift = shift_result if isinstance(shift_result, bool) else shift_result[0]
                is_half_day_checkin = isinstance(shift_result, tuple) and len(shift_result) > 1 and shift_result[1] == "half_day"
                
                has_flexible_timing, flexible_message = self._check_flexible_timing_status(user, today, now)
                
                if not within_shift and not has_flexible_timing:
                    return Response({
                        'detail': 'Check-in allowed 3 hours before shift start, up to 15 minutes after shift start only.'
                    }, status=status.HTTP_400_BAD_REQUEST)
            # If admin reset override is active, skip shift validation for first check-in
        else:
            # Subsequent check-in (after break) - more lenient validation
            # Just check if within reasonable hours (e.g., not in the middle of the night)
            # Use IST for validation
            ist_now = get_ist_time(now)
            current_hour = ist_now.hour
            if current_hour < 6 or current_hour > 23:  # Between 6 AM and 11 PM IST
                return Response({
                    'detail': 'Check-in not allowed during night hours (11 PM - 6 AM IST).'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if day has ended
        if hasattr(attendance, 'day_ended') and attendance.day_ended:
            return Response({
                'detail': 'Day has already ended. Cannot check in again today.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user is already checked in (last session has no check_out)
        if sessions and 'check_out' not in sessions[-1]:
            return Response({
                'detail': 'Already checked in. Please start break first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Add new session
        location = request.data.get('location', {})
        new_session = {
            'check_in': now.isoformat(),
            'location_in': location
        }
        sessions.append(new_session)
        
        attendance.sessions = sessions
        
        # Clear admin reset flag after first successful check-in
        if admin_reset_override:
            attendance.admin_reset_at = None
        
        attendance.save()
        
        # Log the check-in event (with backward compatibility)
        try:
            SessionLog.log_event(
                user=user,
                event_type='check_in',
                date=today,
                session_count=len(sessions),
                location=location,
                request=request
            )
        except Exception as e:
            print(f"Failed to log check-in event: {e}")
        
        return Response({
            'message': 'Checked in successfully',
            'check_in_time': now.isoformat(),
            'session_count': len(sessions)
        })

    @action(detail=False, methods=['post'])
    def start_break(self, request):
        """Start break time for employees with session validation"""
        user = request.user
        now = timezone.now()  # Store UTC
        today = get_ist_date(now)  # Use IST date for business logic
        
        # CRITICAL: Validate active session (with backward compatibility)
        try:
            active_session = SessionLog.get_active_session(user)
            if active_session and active_session.is_session_expired():
                return Response({
                    'detail': 'Session expired. Please log in again to continue.',
                    'session_expired': True
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Update session activity
            if active_session:
                active_session.update_activity()
        except Exception as e:
            # SessionLog table might not exist yet - continue without session management
            print(f"Session management not available in start_break: {e}")
            active_session = None
        
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
        
        # Check if already on break
        if hasattr(attendance, 'break_start_time') and attendance.break_start_time:
            return Response({
                'detail': 'Break already started.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Start break by ending current session (original working logic)
        location = request.data.get('location', {})
        sessions[-1]['check_out'] = now.isoformat()
        sessions[-1]['location_out'] = location
        
        # Mark break start time and update total hours
        attendance.sessions = sessions
        attendance.break_start_time = now
        # Calculate and store total hours from completed sessions
        attendance.total_hours = self._calculate_total_hours(sessions)
        attendance.save()
        
        # Log the start break event (with backward compatibility)
        try:
            SessionLog.log_event(
                user=user,
                event_type='start_break',
                date=today,
                session_count=len(sessions),
                location=location,
                request=request
            )
        except Exception as e:
            print(f"Failed to log start_break event: {e}")
        
        return Response({
            'message': 'Break started successfully',
            'break_start_time': now.isoformat(),
            'session_count': len(sessions)
        })

    @action(detail=False, methods=['post'])
    def end_break(self, request):
        """End break time for employees with session validation"""
        user = request.user
        now = timezone.now()  # Store UTC
        today = get_ist_date(now)  # Use IST date for business logic
        
        # CRITICAL: Validate active session (with backward compatibility)
        try:
            active_session = SessionLog.get_active_session(user)
            if active_session and active_session.is_session_expired():
                return Response({
                    'detail': 'Session expired. Please log in again to continue.',
                    'session_expired': True
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Update session activity
            if active_session:
                active_session.update_activity()
        except Exception as e:
            # SessionLog table might not exist yet - continue without session management
            print(f"Session management not available in end_break: {e}")
            active_session = None
        
        try:
            attendance = Attendance.objects.get(user=user, date=today)
        except Attendance.DoesNotExist:
            return Response({
                'detail': 'No attendance record found for today.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if on break
        if not hasattr(attendance, 'break_start_time') or not attendance.break_start_time:
            return Response({
                'detail': 'Not currently on break.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already ended the day
        if hasattr(attendance, 'day_ended') and attendance.day_ended:
            return Response({
                'detail': 'Day has already ended. Cannot resume work.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # End break by starting new session (original working logic)
        sessions = attendance.sessions or []
        location = request.data.get('location', {})
        
        # Calculate break duration and add to total break time
        break_duration = now - attendance.break_start_time
        if attendance.total_break_time is None:
            attendance.total_break_time = break_duration
        else:
            attendance.total_break_time += break_duration
        
        # Start new session
        new_session = {
            'check_in': now.isoformat(),
            'location_in': location
        }
        sessions.append(new_session)
        
        attendance.sessions = sessions
        attendance.break_start_time = None
        # Calculate and store total hours from completed sessions
        attendance.total_hours = self._calculate_total_hours(sessions)
        attendance.save()
        
        # Log the end break event (with backward compatibility)
        try:
            SessionLog.log_event(
                user=user,
                event_type='end_break',
                date=today,
                session_count=len(sessions),
                location=location,
                request=request
            )
        except Exception as e:
            print(f"Failed to log end_break event: {e}")
        
        return Response({
            'message': 'Break ended successfully. Work resumed.',
            'check_in_time': now.isoformat(),
            'session_count': len(sessions),
            'total_break_time': format_duration(attendance.total_break_time)
        })

    @action(detail=False, methods=['post'])
    def end_of_day(self, request):
        """End of day action for employees with session validation"""
        user = request.user
        now = timezone.now()  # Store UTC
        today = get_ist_date(now)  # Use IST date for business logic
        
        # CRITICAL: Validate active session (with backward compatibility)
        try:
            active_session = SessionLog.get_active_session(user)
            if active_session and active_session.is_session_expired():
                return Response({
                    'detail': 'Session expired. Please log in again to continue.',
                    'session_expired': True
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Update session activity
            if active_session:
                active_session.update_activity()
        except Exception as e:
            # SessionLog table might not exist yet - continue without session management
            print(f"Session management not available in end_of_day: {e}")
            active_session = None
        
        try:
            attendance = Attendance.objects.get(user=user, date=today)
        except Attendance.DoesNotExist:
            return Response({
                'detail': 'No attendance record found for today.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if on break - must end break first
        if hasattr(attendance, 'break_start_time') and attendance.break_start_time:
            return Response({
                'detail': 'Please end your break first before ending the day.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already ended the day
        if hasattr(attendance, 'day_ended') and attendance.day_ended:
            return Response({
                'detail': 'Day has already ended.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        sessions = attendance.sessions or []
        
        # If currently checked in, check out first
        if sessions and 'check_out' not in sessions[-1]:
            location = request.data.get('location', {})
            sessions[-1]['check_out'] = now.isoformat()
            sessions[-1]['location_out'] = location
        
        # Calculate final totals
        attendance.sessions = sessions
        attendance.total_hours = self._calculate_total_hours(sessions)
        attendance.day_ended = True
        attendance.day_end_time = now
        
        # Calculate day status based on working hours
        day_status = self._calculate_day_status(attendance.total_hours, user)
        attendance.day_status = day_status
        
        attendance.save()
        
        # Log the end of day event (with backward compatibility)
        try:
            SessionLog.log_event(
                user=user,
                event_type='end_of_day',
                date=today,
                session_count=len(sessions),
                location=request.data.get('location', {}),
                request=request,
                notes=f'Day status: {day_status}, Total hours: {format_duration(attendance.total_hours)}'
            )
        except Exception as e:
            print(f"Failed to log end_of_day event: {e}")
        
        return Response({
            'message': 'Day ended successfully',
            'end_time': now.isoformat(),
            'total_hours': format_duration(attendance.total_hours),
            'day_status': day_status,
            'total_break_time': format_duration(getattr(attendance, 'total_break_time', timedelta(0)))
        })

    @action(detail=False, methods=['post'])
    def update_session_activity(self, request):
        """Update the last_activity timestamp for the current user's session."""
        user = request.user
        try:
            active_session = SessionLog.get_active_session(user)
            if active_session:
                active_session.update_activity()
                return Response({'status': 'ok'}, status=status.HTTP_200_OK)
            else:
                return Response({'detail': 'No active session found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Session management not available in update_session_activity: {e}")
            return Response({'detail': 'Session management is not available.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _calculate_day_status(self, total_hours, user=None):
        """Calculate day status based on working hours and employee type"""
        if not total_hours:
            return 'Absent'
        
        # Convert to total seconds
        total_seconds = total_hours.total_seconds()
        
        # Check if employee is a half-day employee type
        is_half_day_employee = False
        if user and user.employee_type:
            employee_type_name = user.employee_type.name.lower()
            # Check for various combinations of "half day" in employee type
            half_day_patterns = ['half day', 'halfday', 'half-day']
            is_half_day_employee = any(pattern in employee_type_name for pattern in half_day_patterns)
        
        if is_half_day_employee:
            # Special rules for half-day employees
            # More than 1 hour = Present
            if total_seconds >= 1 * 3600:  # 1 hour or more
                return 'Present'
            # Less than 1 hour = Absent
            else:
                return 'Absent'
        else:
            # Standard rules for full-time employees
            # Less than 3.5 hours = Absent
            if total_seconds < 3.5 * 3600:
                return 'Absent'
            
            # 3.5 to 7.5 hours = Half Day
            if 3.5 * 3600 <= total_seconds < 7.5 * 3600:
                return 'Half Day'
            
            # 7.5 hours or more = Present
            if total_seconds >= 7.5 * 3600:
                return 'Present'
        
        return 'Absent'

    @action(detail=False, methods=['get'])
    def check_admin_intervention_needed(self, request):
        """Check if admin intervention (reset day) is needed for an employee"""
        user_id = request.query_params.get('user_id')
        date_str = request.query_params.get('date')
        
        if not user_id or not date_str:
            return Response({
                'detail': 'user_id and date are required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from accounts.models import User
            
            user = User.objects.get(id=user_id)
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            now = timezone.now()
            today = get_ist_date(now)
            
            # Only check for today or past dates
            if date > today:
                return Response({
                    'needs_intervention': False,
                    'reason': 'Future date'
                })
            
            # Get attendance record
            try:
                attendance = Attendance.objects.get(user=user, date=date)
                
                # If day has ended, admin can reset
                if hasattr(attendance, 'day_ended') and attendance.day_ended:
                    return Response({
                        'needs_intervention': True,
                        'reason': 'Day has ended',
                        'can_reset': True
                    })
                
                # Check if user has any sessions (checked in)
                sessions = attendance.sessions or []
                if len(sessions) > 0:
                    return Response({
                        'needs_intervention': False,
                        'reason': 'User has already checked in'
                    })
                
            except Attendance.DoesNotExist:
                # No attendance record means user never checked in
                pass
            
            # Check if user is on leave
            is_on_leave, leave_message = self._check_leave_status(user, date, now)
            if is_on_leave:
                return Response({
                    'needs_intervention': False,
                    'reason': f'User is on leave: {leave_message}'
                })
            
            # Get user shifts
            shifts = self._get_user_shifts(user)
            if not shifts.exists():
                return Response({
                    'needs_intervention': False,
                    'reason': 'No shift assigned'
                })
            
            # For today, check if user missed the check-in window
            if date == today:
                # Check if current time is past the allowed check-in window
                shift_result = self._is_within_shift_hours(now, shifts, check_in_grace=True)
                within_shift = shift_result if isinstance(shift_result, bool) else shift_result[0]
                
                # Check flexible timing
                has_flexible_timing, flexible_message = self._check_flexible_timing_status(user, date, now)
                
                if not within_shift and not has_flexible_timing:
                    # User is outside allowed check-in window - needs admin intervention
                    return Response({
                        'needs_intervention': True,
                        'reason': 'User missed check-in window (outside 3 hours before to 15 minutes after shift start)',
                        'can_reset': True
                    })
            
            # For past dates, if no attendance record exists, user missed the day
            elif date < today:
                return Response({
                    'needs_intervention': True,
                    'reason': 'User missed attendance for this past date',
                    'can_reset': True
                })
            
            return Response({
                'needs_intervention': False,
                'reason': 'User can still check in normally'
            })
            
        except User.DoesNotExist:
            return Response({
                'detail': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({
                'detail': 'Invalid date format. Use YYYY-MM-DD.'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def admin_reset_day(self, request):
        """Admin action to reset day status and allow employee to check in again"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({
                'detail': 'Only admin can reset day status.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        user_id = request.data.get('user_id')
        date_str = request.data.get('date')
        
        if not user_id or not date_str:
            return Response({
                'detail': 'user_id and date are required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            attendance, created = Attendance.objects.get_or_create(
                user_id=user_id, 
                date=date,
                defaults={'sessions': []}  # Default value for sessions
            )
            
            # No restrictions on admin resets - allow unlimited resets when needed
            # Keep tracking for audit purposes only
            
            # Reset day status but preserve total_break_time (like total_hours)
            attendance.day_ended = False
            attendance.day_end_time = None
            attendance.day_status = None
            attendance.break_start_time = None
            attendance.admin_reset_at = timezone.now()  # Track when admin reset the day
            attendance.admin_reset_count = (attendance.admin_reset_count or 0) + 1  # Increment reset count
            # DO NOT reset total_break_time - preserve it like total_hours
            
            # Fix sessions state - ensure all sessions are properly closed
            sessions = attendance.sessions or []
            if sessions:
                # Close any incomplete sessions (sessions without check_out)
                for session in sessions:
                    if 'check_out' not in session:
                        # Close the incomplete session with current time
                        session['check_out'] = timezone.now().isoformat()
                        session['location_out'] = session.get('location_in', {})
                
                # Update sessions and recalculate total hours
                attendance.sessions = sessions
                attendance.total_hours = self._calculate_total_hours(sessions)
                attendance.day_status = 'Present'  # Set to Present since user has completed sessions
            else:
                # No sessions - user never checked in
                attendance.day_status = None
            
            attendance.save()
            
            # Log the admin reset action for audit trail
            try:
                SessionLog.log_event(
                    user=attendance.user,
                    event_type='admin_reset',
                    date=date,
                    notes=f'Day reset by admin {request.user.username}. Reset count: {attendance.admin_reset_count}.',
                    request=request
                )
            except Exception as e:
                print(f"Failed to log admin reset event: {e}")
            
            return Response({
                'message': 'Day status reset successfully. Employee can check in again.',
                'date': date_str,
                'user_id': user_id,
                'reset_count': attendance.admin_reset_count,
                'info': f'This day has been reset {attendance.admin_reset_count} time(s).' if attendance.admin_reset_count > 1 else 'First reset for this day.'
            })
            
        except Attendance.DoesNotExist:
            return Response({
                'detail': 'No attendance record found for the specified user and date.'
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({
                'detail': 'Invalid date format. Use YYYY-MM-DD.'
            }, status=status.HTTP_400_BAD_REQUEST)

    def _calculate_attendance_status(self, user, date, sessions, total_hours):
        """Calculate attendance status (Present/Absent/Half Day) based on sessions and hours"""
        today = get_current_ist_date()  # Use IST date for business logic
        is_today = date == today
        has_approved_leave = self._check_leave_status(user, date, timezone.now())[0]
        
        # If no sessions recorded
        if not sessions:
            if has_approved_leave:
                return 'On Leave'
            return 'Absent'
        
        # If user has sessions
        if sessions:
            # Check if user has active session (checked in but not out)
            has_active_session = any('check_out' not in session for session in sessions)
            
            # For today's date, if user has checked in, show Active for table but Present for calendar
            if is_today and sessions:
                if has_active_session:
                    return 'Active'  # This will show in table, but calendar should show 'Present'
                else:
                    # Day completed but not ended - show Present
                    return 'Present'
            
            # For past dates or end-of-day calculation, use working hours logic
            total_seconds = 0
            if total_hours:
                time_parts = str(total_hours).split(':')
                hours = int(time_parts[0]) if len(time_parts) > 0 else 0
                minutes = int(time_parts[1]) if len(time_parts) > 1 else 0
                seconds = float(time_parts[2]) if len(time_parts) > 2 else 0
                total_seconds = hours * 3600 + minutes * 60 + seconds
            
            # Get user shifts to determine minimum working hours
            shifts = self._get_user_shifts(user)
            min_hours = 8 * 3600  # Default 8 hours in seconds
            
            if shifts.exists():
                shift = shifts.first()
                start_time = shift.start_time
                end_time = shift.end_time
                
                # Calculate shift duration
                start_seconds = start_time.hour * 3600 + start_time.minute * 60
                end_seconds = end_time.hour * 3600 + end_time.minute * 60
                
                if end_seconds > start_seconds:
                    min_hours = end_seconds - start_seconds
                else:
                    # Overnight shift
                    min_hours = (24 * 3600 - start_seconds) + end_seconds
            
            # Check if employee is a half-day employee type
            is_half_day_employee = False
            if user and user.employee_type:
                employee_type_name = user.employee_type.name.lower()
                # Check for various combinations of "half day" in employee type
                half_day_patterns = ['half day', 'halfday', 'half-day', 'part time', 'parttime', 'part-time']
                is_half_day_employee = any(pattern in employee_type_name for pattern in half_day_patterns)
            
            # Determine status based on working hours and employee type
            if is_half_day_employee:
                # Special rules for half-day employees
                if total_seconds >= 3 * 3600:  # 3 hour or more
                    if has_approved_leave:
                        return 'Present (Despite Leave)'
                    return 'Present'
                else:
                    if has_approved_leave:
                        return 'On Leave'
                    return 'Absent'
            else:
                # Standard rules for full-time employees
                if total_seconds >= 7.5 * 3600:  # 7.5 hours or more
                    if has_approved_leave:
                        return 'Present (Despite Leave)'
                    return 'Present'
                elif total_seconds >= 3.5 * 3600:  # 3.5 to 7.5 hours
                    if has_approved_leave:
                        return 'Half Day (Despite Leave)'
                    return 'Half Day'
                elif total_seconds > 0:  # Has some working time but less than 3.5 hours
                    if has_approved_leave:
                        return 'Half Day (Despite Leave)'
                    return 'Absent'
                else:
                    # Has sessions but no working time (check-in only)
                    if has_approved_leave:
                        return 'On Leave'
                    return 'Absent'
        
        # Fallback
        if has_approved_leave:
            return 'On Leave'
        return 'Absent'

    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get current attendance status for the user - BACKEND IS SOURCE OF TRUTH"""
        user = request.user
        today = get_current_ist_date()  # Use IST date for business logic
        
        # CRITICAL: Check for expired sessions BEFORE returning status
        # Handle case where SessionLog table doesn't exist yet (backward compatibility)
        try:
            expired_count = SessionLog.check_and_handle_expired_sessions()
            if expired_count > 0:
                print(f"Marked {expired_count} expired sessions as inactive")
        except Exception as e:
            # SessionLog table might not exist yet - continue without session management
            print(f"Session management not available: {e}")
            expired_count = 0
        
        # Validate current session (with backward compatibility)
        try:
            active_session = SessionLog.get_active_session(user)
            session_valid = active_session and not active_session.is_session_expired()
        except Exception as e:
            # SessionLog table might not exist yet - assume session is valid
            print(f"Session validation not available: {e}")
            active_session = None
            session_valid = True
        
        # If session is valid, update activity (with backward compatibility)
        if session_valid and active_session:
            try:
                active_session.update_activity()
            except Exception as e:
                print(f"Session activity update failed: {e}")
        
        try:
            attendance = Attendance.objects.get(user=user, date=today)
            sessions = attendance.sessions or []
            
            # BACKEND DETERMINES STATE - not frontend localStorage
            # CRITICAL FIX: Ensure boolean result, not array
            is_checked_in = bool(sessions and 'check_out' not in sessions[-1] and not attendance.day_ended)
            total_sessions = len(sessions)
            completed_sessions = len([s for s in sessions if 'check_out' in s])
            
            # Check if on break - ONLY trust backend state
            # CRITICAL FIX: Ensure boolean result
            is_on_break = bool(
                hasattr(attendance, 'break_start_time') and 
                attendance.break_start_time is not None and 
                not attendance.day_ended
            )
            
            # Check if day ended - BACKEND AUTHORITY
            # CRITICAL FIX: Ensure boolean result
            day_ended = bool(hasattr(attendance, 'day_ended') and attendance.day_ended)
            
            # Session validation only - no auto-end of workday
            # Users must manually end their workday
            
            # Calculate attendance status
            if day_ended:
                attendance_status = getattr(attendance, 'day_status', 'Absent')
                calendar_status = attendance_status  # Same for both when day ended
            else:
                attendance_status = self._calculate_attendance_status(user, today, sessions, attendance.total_hours)
                # For calendar, show 'Present' instead of 'Active' when user has checked in
                calendar_status = 'Present' if attendance_status == 'Active' else attendance_status
            
            # Use stored total hours (calculated from completed sessions)
            total_hours = attendance.total_hours or timedelta(0)
            
            response_data = {
                'date': today,
                'is_checked_in': is_checked_in,  # BACKEND AUTHORITY
                'is_on_break': is_on_break,      # BACKEND AUTHORITY
                'day_ended': day_ended,          # BACKEND AUTHORITY
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'total_hours': format_duration(total_hours),
                'total_break_time': format_duration(getattr(attendance, 'total_break_time', timedelta(0))),
                'attendance_status': attendance_status,  # For table/UI
                'calendar_status': calendar_status,      # For calendar
                'session_valid': session_valid,          # Frontend can use this for session management
            }
            
            if sessions:
                # Only provide last_check_in if there's actually an active session
                if is_checked_in:  # Only if currently checked in (active session)
                    response_data['last_check_in'] = sessions[-1].get('check_in')
                if sessions[-1].get('check_out'):
                    response_data['last_check_out'] = sessions[-1].get('check_out')
            
            if is_on_break:
                response_data['break_start_time'] = attendance.break_start_time.isoformat()
            
            if day_ended:
                response_data['day_end_time'] = attendance.day_end_time.isoformat() if attendance.day_end_time else None
            
            # Check if on leave
            is_on_leave, _ = self._check_leave_status(user, today, timezone.now())
            response_data['is_on_leave'] = is_on_leave
            
            return Response(response_data)
            
        except Attendance.DoesNotExist:
            # Check if on leave when no attendance record
            is_on_leave, _ = self._check_leave_status(user, today, timezone.now())
            attendance_status = 'On Leave' if is_on_leave else 'Absent'
            
            return Response({
                'date': today,
                'is_checked_in': False,          # BACKEND AUTHORITY
                'is_on_break': False,            # BACKEND AUTHORITY
                'day_ended': False,              # BACKEND AUTHORITY
                'total_sessions': 0,
                'completed_sessions': 0,
                'total_hours': '0:00:00',
                'total_break_time': '0:00:00',
                'is_on_leave': is_on_leave,
                'attendance_status': attendance_status,
                'session_valid': session_valid,  # Frontend can use this for session management
            })

    @action(detail=False, methods=['get'])
    def employee_stats(self, request):
        """Get employee statistics for admin dashboard"""
        # Only allow staff/admin to access this endpoint
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        
        from django.contrib.auth import get_user_model
        from leave.models import LeaveApplication
        
        User = get_user_model()
        today = get_current_ist_date()
        
        # Get all active employees (excluding staff/admin)
        active_employees = User.objects.filter(is_active=True, is_staff=False)
        total_employees = active_employees.count()
        
        # Get employees who checked in today
        checked_in_today = Attendance.objects.filter(
            date=today,
            sessions__isnull=False
        ).exclude(sessions=[]).values_list('user_id', flat=True)
        
        # Filter to only include sessions with check_in_time
        checked_in_employees = 0
        for attendance in Attendance.objects.filter(date=today, sessions__isnull=False).exclude(sessions=[]):
            if attendance.sessions and any(session.get('check_in') for session in attendance.sessions):
                checked_in_employees += 1
        
        # Get employees on approved leave today
        on_leave_today = LeaveApplication.objects.filter(
            start_date__lte=today,
            end_date__gte=today,
            status='approved'
        ).values_list('user_id', flat=True).distinct()
        
        on_leave_employees = len(set(on_leave_today))
        
        # Calculate absent employees (Total - Checked In - On Leave)
        absent_employees = max(0, total_employees - checked_in_employees - on_leave_employees)
        
        return Response({
            'total_employees': total_employees,
            'checked_in_employees': checked_in_employees,
            'absent_employees': absent_employees,
            'on_leave_employees': on_leave_employees,
            'date': today
        })

    @action(detail=False, methods=['get'])
    def payroll_stats(self, request):
        """Get payroll statistics for a specific month and year"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        
        year = int(request.query_params.get('year', timezone.now().year))
        month = int(request.query_params.get('month', timezone.now().month))
        
        from calendar import monthrange
        from common.models import Holiday
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Calculate total days in month
        total_days_in_month = monthrange(year, month)[1]
        
        # Calculate Sundays in the month
        sundays_in_month = 0
        for day in range(1, total_days_in_month + 1):
            date_obj = timezone.datetime(year, month, day).date()
            if date_obj.weekday() == 6:  # Sunday is 6
                sundays_in_month += 1
        
        # Get holidays in the month
        start_date = timezone.datetime(year, month, 1).date()
        end_date = timezone.datetime(year, month, total_days_in_month).date()
        
        holidays_in_month = Holiday.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).count()
        
        # Calculate working days (total - sundays - holidays)
        working_days_in_month = total_days_in_month - sundays_in_month - holidays_in_month
        
        # Get total active employees
        total_employees = User.objects.filter(is_active=True, is_staff=False).count()
        
        return Response({
            'total_days_in_month': total_days_in_month,
            'working_days_in_month': working_days_in_month,
            'holidays_and_sundays': sundays_in_month + holidays_in_month,
            'sundays_in_month': sundays_in_month,
            'holidays_in_month': holidays_in_month,
            'total_employees': total_employees,
            'year': year,
            'month': month
        })

    @action(detail=False, methods=['get'])
    def payroll_data(self, request):
        """Get payroll data for all employees for a specific month and year"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        
        year = int(request.query_params.get('year', timezone.now().year))
        month = int(request.query_params.get('month', timezone.now().month))
        
        from calendar import monthrange
        from django.contrib.auth import get_user_model
        from leave.models import LeaveApplication
        
        User = get_user_model()
        
        # Get date range for the month
        start_date = timezone.datetime(year, month, 1).date()
        total_days_in_month = monthrange(year, month)[1]
        end_date = timezone.datetime(year, month, total_days_in_month).date()
        
        # Calculate working days in month (excluding Sundays and holidays)
        working_days = 0
        for day in range(1, total_days_in_month + 1):
            date_obj = timezone.datetime(year, month, day).date()
            if date_obj.weekday() != 6:  # Not Sunday
                working_days += 1
        
        # Subtract holidays
        from common.models import Holiday
        holidays_count = Holiday.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).count()
        working_days -= holidays_count
        
        # Get all active employees
        employees = User.objects.filter(is_active=True, is_staff=False)
        
        payroll_data = []
        
        for employee in employees:
            # Get attendance records for the month
            attendance_records = Attendance.objects.filter(
                user=employee,
                date__gte=start_date,
                date__lte=end_date
            )
            
            # Calculate present days (days with sessions)
            present_days = 0
            for attendance in attendance_records:
                if attendance.sessions and len(attendance.sessions) > 0:
                    # Check if any session has check_in
                    if any(session.get('check_in') for session in attendance.sessions):
                        present_days += 1
            
            # Get approved leave days for the month
            leave_applications = LeaveApplication.objects.filter(
                user=employee,
                start_date__lte=end_date,
                end_date__gte=start_date,
                status='approved'
            )
            
            leave_days = 0
            for leave_app in leave_applications:
                # Calculate overlapping days with the month
                leave_start = max(leave_app.start_date, start_date)
                leave_end = min(leave_app.end_date, end_date)
                
                if leave_start <= leave_end:
                    # Count days in the range
                    current_date = leave_start
                    while current_date <= leave_end:
                        # Only count working days (not Sundays)
                        if current_date.weekday() != 6:
                            leave_days += 1
                        current_date += timezone.timedelta(days=1)
            
            # Calculate absent days (working days - present days - leave days)
            absent_days = max(0, working_days - present_days - leave_days)
            
            payroll_data.append({
                'employee_id': employee.employee_id or employee.username,
                'employee_name': f"{employee.first_name} {employee.last_name}".strip() or employee.username,
                'total_present_days': present_days,
                'total_leave_days': leave_days,
                'total_absent_days': absent_days,
                'working_days': working_days
            })
        
        return Response(payroll_data)

    @action(detail=False, methods=['get'])
    def get_shift_timing(self, request):
        """
        Get the shift timing for the currently authenticated user.
        """
        user = request.user
        shifts = self._get_user_shifts(user)

        if not shifts.exists():
            return Response({
                'detail': 'No shift assigned. Contact admin.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Assuming a user has one primary active shift for simplicity
        shift = shifts.first()

        return Response({
            'start_time': format_time_12hour(shift.start_time),
            'end_time': format_time_12hour(shift.end_time),
            'shift_name': shift.name
        })


    @action(detail=False, methods=['get'])
    def get_shift_timing(self, request):
        """
        Get the shift timing for the currently authenticated user.
        """
        user = request.user
        shifts = self._get_user_shifts(user)

        if not shifts.exists():
            return Response({
                'detail': 'No shift assigned. Contact admin.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Assuming a user has one primary active shift for simplicity
        shift = shifts.first()

        return Response({
            'start_time': format_time_12hour(shift.start_time),
            'end_time': format_time_12hour(shift.end_time),
            'shift_name': shift.name
        })


class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all().order_by('-created_at')
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
    queryset = TimeAdjustment.objects.all().order_by('-created_at')
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
        return qs.order_by('-created_at')

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
    queryset = Approval.objects.all().order_by('-created_at')
    serializer_class = ApprovalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Approval.objects.all().order_by('-created_at')
        # Non-staff can only view approvals where they are the approver
        return Approval.objects.filter(approver=user).order_by('-created_at')



class SessionLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SessionLog - with delete functionality for admin users
    """
    queryset = SessionLog.objects.all().order_by('-timestamp')
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            # Staff can see all session logs
            return SessionLog.objects.all().order_by('-timestamp')
        else:
            # Regular users can only see their own session logs
            return SessionLog.objects.filter(user=user).order_by('-timestamp')
    
    def destroy(self, request, *args, **kwargs):
        """Allow only staff to delete session logs"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Only staff can delete session logs.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        """Prevent manual creation of session logs"""
        return Response({'detail': 'Session logs are created automatically.'}, status=status.HTTP_403_FORBIDDEN)
    
    def update(self, request, *args, **kwargs):
        """Prevent manual updates of session logs"""
        return Response({'detail': 'Session logs cannot be modified.'}, status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=False, methods=['delete'])
    def clear_all_logs(self, request):
        """Clear all session logs - admin only"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Only staff can clear all logs.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get count before deletion
        total_count = SessionLog.objects.count()
        
        # Delete all session logs
        SessionLog.objects.all().delete()
        
        return Response({
            'message': f'Successfully cleared {total_count} session logs.',
            'deleted_count': total_count
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['delete'])
    def clear_user_logs(self, request):
        """Clear all session logs for a specific user - admin only"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Only staff can clear user logs.'}, status=status.HTTP_403_FORBIDDEN)
        
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'detail': 'user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from accounts.models import User
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get count before deletion
        user_logs_count = SessionLog.objects.filter(user=user).count()
        
        # Delete user's session logs
        SessionLog.objects.filter(user=user).delete()
        
        return Response({
            'message': f'Successfully cleared {user_logs_count} session logs for user {user.username}.',
            'deleted_count': user_logs_count,
            'user': user.username
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['delete'])
    def clear_date_range_logs(self, request):
        """Clear session logs within a date range - admin only"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Only staff can clear logs by date range.'}, status=status.HTTP_403_FORBIDDEN)
        
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        if not start_date or not end_date:
            return Response({'detail': 'start_date and end_date are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from datetime import datetime
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response({'detail': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get count before deletion
        date_logs_count = SessionLog.objects.filter(date__gte=start_date_obj, date__lte=end_date_obj).count()
        
        # Delete logs in date range
        SessionLog.objects.filter(date__gte=start_date_obj, date__lte=end_date_obj).delete()
        
        return Response({
            'message': f'Successfully cleared {date_logs_count} session logs from {start_date} to {end_date}.',
            'deleted_count': date_logs_count,
            'start_date': start_date,
            'end_date': end_date
        }, status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        """Delete individual session log and recalculate attendance - admin only"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'detail': 'Only staff can delete session logs.'}, status=status.HTTP_403_FORBIDDEN)
        
        session_log = self.get_object()
        user = session_log.user
        date = session_log.date
        
        # Delete the session log
        session_log.delete()
        
        # Recalculate attendance for that date
        self._recalculate_attendance_for_date(user, date)
        
        return Response({
            'message': 'Session log deleted and attendance recalculated successfully.',
            'user': user.username,
            'date': str(date)
        }, status=status.HTTP_200_OK)
    
    def _recalculate_attendance_for_date(self, user, date):
        """Recalculate attendance totals based on remaining session logs"""
        try:
            attendance = Attendance.objects.get(user=user, date=date)
            
            # Get remaining session logs for this date
            remaining_logs = SessionLog.objects.filter(
                user=user, 
                date=date,
                event_type__in=['check_in', 'check_out', 'start_break', 'end_break']
            ).order_by('timestamp')
            
            # Rebuild sessions from remaining logs
            sessions = []
            current_session = {}
            
            for log in remaining_logs:
                if log.event_type == 'check_in':
                    if current_session and 'check_out' not in current_session:
                        # Previous session was incomplete, close it
                        sessions.append(current_session)
                    current_session = {
                        'check_in': log.timestamp.isoformat(),
                        'location_in': log.location or {}
                    }
                elif log.event_type == 'check_out' and current_session:
                    current_session['check_out'] = log.timestamp.isoformat()
                    current_session['location_out'] = log.location or {}
                    sessions.append(current_session)
                    current_session = {}
                elif log.event_type == 'start_break' and current_session:
                    # End current session for break
                    current_session['check_out'] = log.timestamp.isoformat()
                    current_session['location_out'] = log.location or {}
                    sessions.append(current_session)
                    current_session = {}
                elif log.event_type == 'end_break':
                    # Start new session after break
                    current_session = {
                        'check_in': log.timestamp.isoformat(),
                        'location_in': log.location or {}
                    }
            
            # Add incomplete session if exists
            if current_session:
                sessions.append(current_session)
            
            # Update attendance record
            attendance.sessions = sessions
            
            # Recalculate totals
            from datetime import timedelta
            total_seconds = 0
            break_seconds = 0
            
            # Calculate working hours from completed sessions
            for session in sessions:
                if 'check_in' in session and 'check_out' in session:
                    check_in = timezone.datetime.fromisoformat(session['check_in'])
                    check_out = timezone.datetime.fromisoformat(session['check_out'])
                    duration = check_out - check_in
                    total_seconds += duration.total_seconds()
            
            # Calculate break time between sessions
            for i in range(1, len(sessions)):
                prev_session = sessions[i-1]
                curr_session = sessions[i]
                
                if 'check_out' in prev_session and 'check_in' in curr_session:
                    prev_checkout = timezone.datetime.fromisoformat(prev_session['check_out'])
                    curr_checkin = timezone.datetime.fromisoformat(curr_session['check_in'])
                    break_duration = curr_checkin - prev_checkout
                    break_seconds += break_duration.total_seconds()
            
            attendance.total_hours = timedelta(seconds=total_seconds) if total_seconds > 0 else None
            attendance.total_break_time = timedelta(seconds=break_seconds) if break_seconds > 0 else None
            
            # Reset break start time if no active break
            attendance.break_start_time = None
            
            # Check if day should still be marked as ended
            end_of_day_logs = SessionLog.objects.filter(
                user=user, 
                date=date,
                event_type='end_of_day'
            ).exists()
            
            if not end_of_day_logs:
                attendance.day_ended = False
                attendance.day_end_time = None
                attendance.day_status = None
            
            attendance.save()
            
        except Attendance.DoesNotExist:
            # If no attendance record exists, create one with empty sessions
            Attendance.objects.create(
                user=user,
                date=date,
                sessions=[],
                total_hours=None,
                total_break_time=None
            )
    
    def get_serializer_class(self):
        # Create a simple serializer for SessionLog
        from rest_framework import serializers
        
        class SessionLogSerializer(serializers.ModelSerializer):
            user_name = serializers.CharField(source='user.get_full_name', read_only=True)
            user_username = serializers.CharField(source='user.username', read_only=True)
            
            class Meta:
                model = SessionLog
                fields = ['id', 'user', 'user_name', 'user_username', 'event_type', 'timestamp', 'date', 'session_count', 'location', 'notes', 'ip_address', 'is_session_active', 'last_activity']
                read_only_fields = ['id', 'user', 'user_name', 'user_username', 'event_type', 'timestamp', 'date', 'session_count', 'location', 'notes', 'ip_address', 'is_session_active', 'last_activity']
        
        return SessionLogSerializer