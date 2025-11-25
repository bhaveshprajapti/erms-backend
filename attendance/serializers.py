from rest_framework import serializers
from .models import Attendance, LeaveRequest, TimeAdjustment, Approval
from datetime import timedelta

def format_duration(duration):
    """Format timedelta to HH:MM:SS format"""
    if not duration:
        return '0:00:00'
    
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    return f"{hours}:{minutes:02d}:{seconds:02d}"

class AttendanceSerializer(serializers.ModelSerializer):
    calendar_status = serializers.SerializerMethodField()
    attendance_status = serializers.SerializerMethodField()
    total_hours = serializers.SerializerMethodField()
    total_break_time = serializers.SerializerMethodField()
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    employee_type = serializers.SerializerMethodField()
    shift_time = serializers.SerializerMethodField()
    check_in_time = serializers.SerializerMethodField()
    check_out_time = serializers.SerializerMethodField()
    result_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Attendance
        fields = '__all__'
    
    def get_calendar_status(self, obj):
        """Get calendar-appropriate status"""
        from .views import AttendanceViewSet
        viewset = AttendanceViewSet()
        
        sessions = obj.sessions or []
        
        # If day ended, use the final status
        if hasattr(obj, 'day_ended') and obj.day_ended and hasattr(obj, 'day_status') and obj.day_status:
            return obj.day_status
        
        # Calculate status using the viewset method
        status = viewset._calculate_attendance_status(obj.user, obj.date, sessions, obj.total_hours)
        
        # For calendar, convert 'Active' to 'Present'
        return 'Present' if status == 'Active' else status
    
    def get_attendance_status(self, obj):
        """Get UI-appropriate status"""
        from .views import AttendanceViewSet
        viewset = AttendanceViewSet()
        
        sessions = obj.sessions or []
        
        # If day ended, use the final status
        if hasattr(obj, 'day_ended') and obj.day_ended and hasattr(obj, 'day_status') and obj.day_status:
            return obj.day_status
        
        # Calculate status using the viewset method
        return viewset._calculate_attendance_status(obj.user, obj.date, sessions, obj.total_hours)
    
    def get_total_hours(self, obj):
        """Format total hours as HH:MM:SS"""
        return format_duration(obj.total_hours) if obj.total_hours else '0:00:00'
    
    def get_total_break_time(self, obj):
        """Format total break time as HH:MM:SS"""
        return format_duration(getattr(obj, 'total_break_time', timedelta(0)))
    
    def get_employee_type(self, obj):
        """Get employee type name"""
        if obj.user and obj.user.employee_type:
            return obj.user.employee_type.name
        return None
    
    def get_shift_time(self, obj):
        """Get shift time range"""
        if obj.user:
            shifts = obj.user.shifts.filter(is_active=True)
            if shifts.exists():
                shift = shifts.first()
                return f"{shift.start_time.strftime('%I:%M %p')} - {shift.end_time.strftime('%I:%M %p')}"
        return None
    
    def get_check_in_time(self, obj):
        """Get first check-in time of the day"""
        sessions = obj.sessions or []
        if sessions and 'check_in' in sessions[0]:
            from datetime import datetime
            from common.timezone_utils import get_ist_time
            check_in = datetime.fromisoformat(sessions[0]['check_in'])
            ist_time = get_ist_time(check_in)
            return ist_time.strftime('%I:%M %p')
        return None
    
    def get_check_out_time(self, obj):
        """Get last check-out time of the day"""
        sessions = obj.sessions or []
        if sessions:
            # Find the last session with check_out
            for session in reversed(sessions):
                if 'check_out' in session:
                    from datetime import datetime
                    from common.timezone_utils import get_ist_time
                    check_out = datetime.fromisoformat(session['check_out'])
                    ist_time = get_ist_time(check_out)
                    return ist_time.strftime('%I:%M %p')
        return None
    
    def get_result_status(self, obj):
        """Get result status (Present, Absent, Half Day, etc.)"""
        from .views import AttendanceViewSet
        viewset = AttendanceViewSet()
        
        sessions = obj.sessions or []
        
        # If day ended, use the final status
        if hasattr(obj, 'day_ended') and obj.day_ended and hasattr(obj, 'day_status') and obj.day_status:
            return obj.day_status
        
        # If no sessions, mark as Absent
        if not sessions:
            return 'Absent'
        
        # Calculate status using the viewset method
        status = viewset._calculate_attendance_status(obj.user, obj.date, sessions, obj.total_hours)
        
        # Map status to result
        if status in ['Present', 'Active']:
            return 'Present'
        elif status == 'Half Day':
            return 'Half Day'
        elif status == 'Absent':
            return 'Absent'
        else:
            return status

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
