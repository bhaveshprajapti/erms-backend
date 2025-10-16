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
