from rest_framework import serializers
from django.core.exceptions import ValidationError
from datetime import date, datetime, timedelta
from .models import (
    FlexibleTimingType, FlexibleTimingRequest, FlexibleTimingBalance, 
    FlexibleTimingPolicy
)


class FlexibleTimingTypeSerializer(serializers.ModelSerializer):
    """Serializer for flexible timing types"""
    
    class Meta:
        model = FlexibleTimingType
        fields = [
            'id', 'name', 'code', 'description', 'max_duration_minutes',
            'max_per_month', 'requires_approval', 'advance_notice_hours',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class FlexibleTimingRequestSerializer(serializers.ModelSerializer):
    """Serializer for flexible timing requests (read)"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    timing_type_name = serializers.CharField(source='timing_type.name', read_only=True)
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    can_cancel = serializers.SerializerMethodField()
    can_use = serializers.SerializerMethodField()
    monthly_usage_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FlexibleTimingRequest
        fields = [
            'id', 'user', 'user_name', 'timing_type', 'timing_type_name',
            'request_type', 'request_type_display', 'requested_date',
            'duration_minutes', 'start_time', 'end_time', 'reason',
            'is_emergency', 'status', 'status_display', 'approved_by',
            'approved_by_name', 'approved_at', 'rejection_reason',
            'admin_comments', 'used_at', 'actual_duration_minutes',
            'applied_at', 'updated_at', 'can_cancel', 'can_use',
            'monthly_usage_count'
        ]
        read_only_fields = [
            'user', 'approved_by', 'approved_at', 'used_at', 
            'applied_at', 'updated_at'
        ]

    def get_can_cancel(self, obj):
        """Check if request can be cancelled"""
        return obj.can_be_cancelled()

    def get_can_use(self, obj):
        """Check if request can be used"""
        return obj.can_be_used()

    def get_monthly_usage_count(self, obj):
        """Get monthly usage count"""
        return obj.get_monthly_usage_count()


class FlexibleTimingRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating flexible timing requests"""
    
    class Meta:
        model = FlexibleTimingRequest
        fields = [
            'timing_type', 'request_type', 'requested_date',
            'duration_minutes', 'start_time', 'end_time', 'reason',
            'is_emergency'
        ]

    def validate_requested_date(self, value):
        """Validate requested date"""
        if value < date.today():
            raise serializers.ValidationError("Cannot request flexible timing for past dates")
        return value

    def validate_duration_minutes(self, value):
        """Validate duration"""
        if value <= 0:
            raise serializers.ValidationError("Duration must be greater than 0")
        if value > 480:  # 8 hours max
            raise serializers.ValidationError("Duration cannot exceed 8 hours (480 minutes)")
        return value

    def validate(self, data):
        """Validate the entire request"""
        timing_type = data.get('timing_type')
        requested_date = data.get('requested_date')
        duration_minutes = data.get('duration_minutes')
        is_emergency = data.get('is_emergency', False)
        
        # Validate against timing type limits
        if timing_type and duration_minutes:
            if duration_minutes > timing_type.max_duration_minutes:
                raise serializers.ValidationError(
                    f"Duration cannot exceed {timing_type.max_duration_minutes} minutes for {timing_type.name}"
                )
        
        # Validate advance notice (unless emergency)
        if timing_type and requested_date and not is_emergency:
            notice_required = timedelta(hours=timing_type.advance_notice_hours)
            request_datetime = datetime.combine(requested_date, datetime.min.time())
            if datetime.now() + notice_required > request_datetime:
                raise serializers.ValidationError(
                    f"Minimum {timing_type.advance_notice_hours} hours advance notice required"
                )
        
        # Check monthly limit
        if timing_type and requested_date:
            user = self.context['request'].user
            existing_count = FlexibleTimingRequest.objects.filter(
                user=user,
                timing_type=timing_type,
                requested_date__year=requested_date.year,
                requested_date__month=requested_date.month,
                status__in=['pending', 'approved', 'used']
            ).count()
            
            if self.instance:
                # Exclude current instance when updating
                existing_count = existing_count - 1 if existing_count > 0 else 0
            
            if existing_count >= timing_type.max_per_month:
                raise serializers.ValidationError(
                    f"Monthly limit of {timing_type.max_per_month} requests exceeded for {timing_type.name}"
                )
        
        # Validate custom timing fields
        request_type = data.get('request_type')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if request_type == 'custom':
            if not start_time or not end_time:
                raise serializers.ValidationError(
                    "Start time and end time are required for custom timing requests"
                )
            if start_time >= end_time:
                raise serializers.ValidationError(
                    "End time must be after start time"
                )
        
        return data


class FlexibleTimingBalanceSerializer(serializers.ModelSerializer):
    """Serializer for flexible timing balances"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    timing_type_name = serializers.CharField(source='timing_type.name', read_only=True)
    timing_type_code = serializers.CharField(source='timing_type.code', read_only=True)
    remaining_count = serializers.ReadOnlyField()
    can_request_more = serializers.ReadOnlyField()
    
    class Meta:
        model = FlexibleTimingBalance
        fields = [
            'id', 'user', 'user_name', 'timing_type', 'timing_type_name',
            'timing_type_code', 'year', 'month', 'total_allowed',
            'used_count', 'pending_count', 'remaining_count',
            'can_request_more', 'total_duration_used', 'total_duration_pending',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'user', 'timing_type', 'used_count', 'pending_count',
            'total_duration_used', 'total_duration_pending',
            'created_at', 'updated_at'
        ]


class FlexibleTimingPolicySerializer(serializers.ModelSerializer):
    """Serializer for flexible timing policies"""
    applicable_roles_names = serializers.StringRelatedField(
        source='applicable_roles', many=True, read_only=True
    )
    
    class Meta:
        model = FlexibleTimingPolicy
        fields = [
            'id', 'name', 'applicable_roles', 'applicable_roles_names',
            'is_active', 'requires_manager_approval', 'requires_hr_approval',
            'allow_emergency_requests', 'emergency_auto_approve',
            'emergency_max_duration', 'notify_manager', 'notify_hr',
            'notify_team', 'min_team_strength_required', 'effective_from',
            'effective_to', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        """Validate policy dates"""
        effective_from = data.get('effective_from')
        effective_to = data.get('effective_to')
        
        if effective_from and effective_to:
            if effective_from >= effective_to:
                raise serializers.ValidationError(
                    "Effective from date must be before effective to date"
                )
        
        return data


class FlexibleTimingRequestSummarySerializer(serializers.Serializer):
    """Serializer for flexible timing request summaries"""
    timing_type_name = serializers.CharField()
    total_requests = serializers.IntegerField()
    pending_requests = serializers.IntegerField()
    approved_requests = serializers.IntegerField()
    rejected_requests = serializers.IntegerField()
    used_requests = serializers.IntegerField()
    total_duration_minutes = serializers.IntegerField()


class FlexibleTimingDashboardSerializer(serializers.Serializer):
    """Serializer for flexible timing dashboard data"""
    user_name = serializers.CharField()
    department = serializers.CharField()
    current_month_usage = FlexibleTimingBalanceSerializer(many=True)
    recent_requests = FlexibleTimingRequestSerializer(many=True)
    upcoming_approved = FlexibleTimingRequestSerializer(many=True)
