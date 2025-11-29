from rest_framework import serializers
from django.core.exceptions import ValidationError
from datetime import date, datetime, timedelta
from decimal import Decimal
from .models import (
    LeaveType, LeaveTypePolicy, LeaveBalance, LeaveApplication, 
    LeaveApplicationComment, OverallLeavePolicy, LeaveBlackoutDate,
    LeaveBalanceAudit, LeaveCalendar, FlexibleTimingType, FlexibleTimingRequest,
    FlexibleTimingBalance, FlexibleTimingPolicy
)

# Import flexible timing serializers
from .flexible_timing_serializers import (
    FlexibleTimingTypeSerializer, FlexibleTimingRequestSerializer,
    FlexibleTimingRequestCreateSerializer, FlexibleTimingBalanceSerializer,
    FlexibleTimingPolicySerializer, FlexibleTimingRequestSummarySerializer,
    FlexibleTimingDashboardSerializer
)
from django.db import models
from accounts.models import User, Role


class LeaveTypeSerializer(serializers.ModelSerializer):
    """Serializer for leave types"""
    policies_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LeaveType
        fields = [
            'id', 'name', 'code', 'is_paid', 'description', 
            'color_code', 'icon', 'is_active', 'created_at', 
            'updated_at', 'policies_count'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_policies_count(self, obj):
        return obj.policies.filter(is_active=True).count()


class LeaveTypePolicySerializer(serializers.ModelSerializer):
    """Serializer for leave type policies"""
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)
    applicable_roles_names = serializers.SerializerMethodField()
    
    class Meta:
        model = LeaveTypePolicy
        fields = [
            'id', 'name', 'leave_type', 'leave_type_name', 'leave_type_code',
            'applicable_roles', 'applicable_roles_names', 'applicable_gender',
            'annual_quota', 'accrual_frequency', 'accrual_rate',
            'max_per_week', 'max_per_month', 'max_per_year', 'max_consecutive_days', 'max_occurrences_per_month',
            'min_notice_days', 'requires_approval', 'auto_approve_threshold',
            'carry_forward_enabled', 'carry_forward_limit', 'carry_forward_expiry_months',
            'min_tenure_days', 'available_during_probation',
            'include_weekends', 'include_holidays',
            'is_active', 'effective_from', 'effective_to',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_applicable_roles_names(self, obj):
        return [role.display_name for role in obj.applicable_roles.all()]
    
    def validate(self, data):
        """Validate policy data"""
        # Convert empty strings and 0 to None for optional decimal fields
        # This ensures "no limit" is properly stored as NULL in database
        optional_decimal_fields = [
            'max_per_week', 'max_per_month', 'max_per_year', 
            'max_consecutive_days', 'max_occurrences_per_month'
        ]
        for field in optional_decimal_fields:
            if field in data:
                value = data[field]
                # Convert empty string, 0, or None to None
                if value == '' or value == 0 or value is None:
                    data[field] = None
        
        # Handle auto_approve_threshold (integer field)
        if 'auto_approve_threshold' in data:
            value = data['auto_approve_threshold']
            if value == '' or value == 0 or value is None:
                data['auto_approve_threshold'] = None
        
        if data.get('effective_to') and data.get('effective_from'):
            if data['effective_to'] <= data['effective_from']:
                raise serializers.ValidationError("Effective to date must be after effective from date")
        
        if data.get('carry_forward_enabled') and not data.get('carry_forward_limit'):
            raise serializers.ValidationError("Carry forward limit is required when carry forward is enabled")
        
        return data


class LeaveBalanceSerializer(serializers.ModelSerializer):
    """Serializer for leave balances"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)
    leave_type_color = serializers.CharField(source='leave_type.color_code', read_only=True)
    policy_name = serializers.CharField(source='policy.name', read_only=True)
    
    # Calculated fields
    total_available = serializers.ReadOnlyField()
    remaining_balance = serializers.ReadOnlyField()
    pending_balance = serializers.ReadOnlyField()
    
    class Meta:
        model = LeaveBalance
        fields = [
            'id', 'user', 'user_name', 'user_username',
            'leave_type', 'leave_type_name', 'leave_type_code', 'leave_type_color',
            'policy', 'policy_name', 'year',
            'opening_balance', 'accrued_balance', 'used_balance', 
            'carried_forward', 'adjustment',
            'total_available', 'remaining_balance', 'pending_balance',
            'used_this_week', 'used_this_month',
            'last_accrual_date', 'last_reset_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'total_available', 'remaining_balance', 'pending_balance']


class LeaveApplicationCommentSerializer(serializers.ModelSerializer):
    """Serializer for leave application comments"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = LeaveApplicationComment
        fields = ['id', 'user', 'user_name', 'comment', 'is_internal', 'created_at']
        read_only_fields = ['created_at']


class LeaveApplicationSerializer(serializers.ModelSerializer):
    """Serializer for leave applications"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)
    leave_type_color = serializers.CharField(source='leave_type.color_code', read_only=True)
    policy_name = serializers.CharField(source='policy.name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    
    # Comments
    comments = LeaveApplicationCommentSerializer(many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()
    
    # Status helpers
    can_be_cancelled = serializers.ReadOnlyField()
    can_be_edited = serializers.ReadOnlyField()
    can_be_deleted_by_user = serializers.ReadOnlyField()
    can_be_deleted_by_admin = serializers.ReadOnlyField()
    
    # Duration helpers
    duration_text = serializers.SerializerMethodField()
    
    class Meta:
        model = LeaveApplication
        fields = [
            'id', 'user', 'user_name', 'user_username',
            'leave_type', 'leave_type_name', 'leave_type_code', 'leave_type_color',
            'policy', 'policy_name',
            'start_date', 'end_date', 'total_days', 'duration_text',
            'is_half_day', 'half_day_period',
            'reason', 'emergency_contact', 'emergency_phone', 'work_handover',
            'status', 'approved_by', 'approved_by_name', 'approved_at',
            'rejection_reason', 'admin_comments',
            'applied_at', 'updated_at',
            'attachment', 'comments', 'comments_count',
            'can_be_cancelled', 'can_be_edited', 'can_be_deleted_by_user', 'can_be_deleted_by_admin'
        ]
        read_only_fields = [
            'applied_at', 'updated_at', 'approved_by', 'approved_at',
            'can_be_cancelled', 'can_be_edited', 'can_be_deleted_by_user', 'can_be_deleted_by_admin'
        ]
    
    def get_comments_count(self, obj):
        return obj.comments.count()
    
    def get_duration_text(self, obj):
        if obj.is_half_day:
            return f"Half day ({obj.half_day_period})"
        elif obj.total_days == 1:
            return "1 day"
        else:
            return f"{obj.total_days} days"
    
    def validate(self, data):
        """Validate leave application"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        leave_type = data.get('leave_type')
        is_half_day = data.get('is_half_day', False)
        
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError("Start date cannot be after end date")
            
            if is_half_day and start_date != end_date:
                raise serializers.ValidationError("Half day leave must have same start and end date")
        
        # Check if user has sufficient balance
        user = self.context['request'].user if 'request' in self.context else data.get('user')
        if user and leave_type and start_date and end_date:
            # Check for date conflicts with existing requests
            existing_requests = LeaveApplication.objects.filter(
                user=user,
                status__in=['pending', 'approved']  # Only check active requests
            ).exclude(
                id=self.instance.id if self.instance else None  # Exclude current instance when updating
            )
            
            # Check for overlapping dates
            overlapping_requests = existing_requests.filter(
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            
            if overlapping_requests.exists():
                overlapping_request = overlapping_requests.first()
                raise serializers.ValidationError(
                    f"You already have a leave request from {overlapping_request.start_date} to {overlapping_request.end_date} "
                    f"that overlaps with the selected dates. Please choose different dates."
                )
            
            try:
                balance = LeaveBalance.objects.get(
                    user=user,
                    leave_type=leave_type,
                    year=start_date.year
                )
                
                # Calculate days needed
                if is_half_day:
                    days_needed = Decimal('0.5')
                else:
                    days_needed = Decimal(str((end_date - start_date).days + 1))
                
                can_apply, message = balance.can_apply_for_days(days_needed, start_date)
                if not can_apply:
                    raise serializers.ValidationError(message)
                    
            except LeaveBalance.DoesNotExist:
                raise serializers.ValidationError(f"No leave balance found for {leave_type.name} in {start_date.year}")
        
        return data
    
    def create(self, validated_data):
        """Create leave application with auto-calculated total_days"""
        # If total_days is provided, use it; otherwise it will be calculated in clean()
        # The model's save() method calls clean() which recalculates total_days
        instance = super().create(validated_data)
        # Ensure clean() was called to calculate total_days
        if instance.total_days == 0 and instance.start_date and instance.end_date:
            instance.clean()
            instance.save()
        return instance


class LeaveApplicationCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating leave applications"""
    
    class Meta:
        model = LeaveApplication
        fields = [
            'leave_type', 'start_date', 'end_date', 'is_half_day', 
            'half_day_period', 'reason', 'emergency_contact', 
            'emergency_phone', 'work_handover', 'attachment'
        ]
    
    def validate(self, data):
        """Validate and auto-assign policy"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        leave_type = data.get('leave_type')
        is_half_day = data.get('is_half_day', False)
        
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError("Start date cannot be after end date")
            
            if is_half_day and start_date != end_date:
                raise serializers.ValidationError("Half day leave must have same start and end date")
        
        user = self.context['request'].user
        if user and leave_type and start_date and end_date:
            # Check for date conflicts with existing requests
            existing_requests = LeaveApplication.objects.filter(
                user=user,
                status__in=['pending', 'approved']  # Only check active requests
            ).exclude(
                id=self.instance.id if self.instance else None  # Exclude current instance when updating
            )
            
            # Check for overlapping dates
            overlapping_requests = existing_requests.filter(
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            
            if overlapping_requests.exists():
                overlapping_request = overlapping_requests.first()
                raise serializers.ValidationError(
                    f"You already have a leave request from {overlapping_request.start_date} to {overlapping_request.end_date} "
                    f"that overlaps with the selected dates. Please choose different dates."
                )
        
        # Auto-assign applicable policy and validate against it
        if leave_type and user:
            # Find the most suitable policy for this user and leave type
            applicable_policies = LeaveTypePolicy.objects.filter(
                leave_type=leave_type,
                is_active=True,
                effective_from__lte=date.today()
            ).filter(
                models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=date.today())
            )
            
            applicable_policy = None
            for policy in applicable_policies:
                if policy.is_applicable_for_user(user):
                    applicable_policy = policy
                    data['policy'] = policy
                    break
            
            # Validate against leave balance and policy limits
            if applicable_policy and start_date and end_date:
                # Get or create leave balance for current year
                from .models import LeaveBalance
                balance, created = LeaveBalance.objects.get_or_create(
                    user=user,
                    leave_type=leave_type,
                    year=start_date.year,
                    defaults={
                        'policy': applicable_policy,
                        'opening_balance': applicable_policy.annual_quota or 0
                    }
                )
                
                # Calculate days for this request
                if is_half_day and start_date == end_date:
                    request_days = Decimal('0.5')
                else:
                    days_count = (end_date - start_date).days + 1
                    if applicable_policy and not applicable_policy.include_weekends:
                        # Calculate working days only (exclude Sunday only)
                        working_days = 0
                        current_date = start_date
                        while current_date <= end_date:
                            if current_date.weekday() != 6:  # Monday = 0, Sunday = 6
                                working_days += 1
                            current_date += timedelta(days=1)
                        days_count = working_days
                    request_days = Decimal(str(days_count))
                
                # Validate against balance and policy limits for single month
                can_apply, error_message = balance.can_apply_for_days(request_days, start_date, end_date)
                if not can_apply:
                    raise serializers.ValidationError(error_message)
                
                # Cross-month validation: check if leave spans multiple months
                if start_date.month != end_date.month or start_date.year != end_date.year:
                    # Calculate days per month
                    days_per_month = {}
                    current_date = start_date
                    while current_date <= end_date:
                        key = (current_date.year, current_date.month)
                        day_value = Decimal('0.5') if is_half_day else Decimal('1')
                        
                        # Skip Sundays if weekends not included
                        if applicable_policy and not applicable_policy.include_weekends:
                            if current_date.weekday() == 6:  # Sunday
                                current_date += timedelta(days=1)
                                continue
                        
                        if key in days_per_month:
                            days_per_month[key] += day_value
                        else:
                            days_per_month[key] = day_value
                        
                        current_date += timedelta(days=1)
                        if is_half_day:
                            break
                    
                    # Validate balance for each month
                    insufficient_months = []
                    for (year, month), days_needed in days_per_month.items():
                        month_balance, _ = LeaveBalance.objects.get_or_create(
                            user=user,
                            leave_type=leave_type,
                            year=year,
                            defaults={
                                'policy': applicable_policy,
                                'opening_balance': applicable_policy.annual_quota or 0
                            }
                        )
                        
                        # Check if this month has enough balance
                        available = month_balance.remaining_balance
                        if available < days_needed:
                            month_name = date(year, month, 1).strftime('%B %Y')
                            insufficient_months.append(
                                f"{month_name}: need {days_needed} days, available {available} days"
                            )
                    
                    if insufficient_months:
                        raise serializers.ValidationError(
                            f"Insufficient balance for cross-month leave. " + "; ".join(insufficient_months)
                        )
        
        return data


class LeaveApplicationApprovalSerializer(serializers.Serializer):
    """Serializer for approving/rejecting leave applications"""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    comments = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        if data['action'] == 'reject' and not data.get('rejection_reason'):
            raise serializers.ValidationError("Rejection reason is required when rejecting an application")
        return data


class LeaveCalendarSerializer(serializers.ModelSerializer):
    """Serializer for leave calendar view"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    leave_type_name = serializers.CharField(source='leave_application.leave_type.name', read_only=True)
    leave_type_color = serializers.CharField(source='leave_application.leave_type.color_code', read_only=True)
    
    class Meta:
        model = LeaveCalendar
        fields = [
            'id', 'user', 'user_name', 'date', 
            'leave_type_name', 'leave_type_color',
            'is_half_day', 'half_day_period'
        ]


class UserLeaveStatsSerializer(serializers.Serializer):
    """Serializer for user leave statistics"""
    user_id = serializers.IntegerField()
    user_name = serializers.CharField()
    leave_type = serializers.CharField()
    leave_type_code = serializers.CharField()
    total_available = serializers.DecimalField(max_digits=7, decimal_places=2)
    used_balance = serializers.DecimalField(max_digits=7, decimal_places=2)
    remaining_balance = serializers.DecimalField(max_digits=7, decimal_places=2)
    pending_applications = serializers.IntegerField()


class LeaveReportSerializer(serializers.Serializer):
    """Serializer for leave reports"""
    period = serializers.CharField()
    total_applications = serializers.IntegerField()
    approved_applications = serializers.IntegerField()
    rejected_applications = serializers.IntegerField()
    pending_applications = serializers.IntegerField()
    total_days_taken = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    # By leave type
    by_leave_type = serializers.DictField(child=serializers.IntegerField())
    
    # By department/role
    by_role = serializers.DictField(child=serializers.IntegerField())


class BulkLeaveBalanceUpdateSerializer(serializers.Serializer):
    """Serializer for bulk updating leave balances"""
    user_ids = serializers.ListField(child=serializers.IntegerField())
    leave_type = serializers.PrimaryKeyRelatedField(queryset=LeaveType.objects.all())
    year = serializers.IntegerField()
    opening_balance = serializers.DecimalField(max_digits=7, decimal_places=2, required=False)
    adjustment = serializers.DecimalField(max_digits=7, decimal_places=2, required=False)
    
    def validate_year(self, value):
        current_year = date.today().year
        if value < current_year - 1 or value > current_year + 1:
            raise serializers.ValidationError("Year must be within one year of current year")
        return value