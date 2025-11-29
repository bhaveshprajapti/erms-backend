from django.shortcuts import render
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import date, timedelta, datetime
from decimal import Decimal
from django.db import transaction

from .models import (
    LeaveType, LeaveTypePolicy, LeaveBalance, 
    LeaveApplication, LeaveApplicationComment, LeaveCalendar,
    FlexibleTimingType, FlexibleTimingRequest, FlexibleTimingBalance
)
from .serializers import (
    LeaveTypeSerializer, LeaveTypePolicySerializer, LeaveBalanceSerializer,
    LeaveApplicationSerializer, LeaveApplicationCreateSerializer,
    LeaveApplicationApprovalSerializer, LeaveApplicationCommentSerializer,
    LeaveCalendarSerializer, UserLeaveStatsSerializer, LeaveReportSerializer,
    BulkLeaveBalanceUpdateSerializer, FlexibleTimingTypeSerializer,
    FlexibleTimingRequestSerializer, FlexibleTimingBalanceSerializer
)
from accounts.models import User

# Import the flexible timing views from the separate file
from .flexible_timing_views import (
    FlexibleTimingTypeViewSet,
    FlexibleTimingRequestViewSet,
    FlexibleTimingBalanceViewSet
)


class LeaveTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing leave types"""
    queryset = LeaveType.objects.all().order_by('-created_at')
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        return queryset.order_by('-created_at')
    
    def perform_update(self, serializer):
        """Handle leave type status changes with proper validation"""
        leave_type = self.get_object()
        old_is_active = leave_type.is_active
        new_is_active = serializer.validated_data.get('is_active', old_is_active)
        
        # If deactivating leave type, check if it's used in active policies
        if old_is_active and not new_is_active:
            active_policies = LeaveTypePolicy.objects.filter(
                leave_type=leave_type,
                is_active=True
            )
            if active_policies.exists():
                from rest_framework.exceptions import ValidationError
                raise ValidationError({
                    'is_active': "Cannot deactivate leave type. It is currently used in active policies. "
                               "Please deactivate all related policies first."
                })
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Handle leave type deletion with proper validation"""
        # Check if it's used in any policies (active or inactive)
        policies = LeaveTypePolicy.objects.filter(leave_type=instance)
        if policies.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                "Cannot delete leave type. It is used in leave policies. "
                "Please delete all related policies first."
            )
        
        # Check if there are any leave applications
        applications = LeaveApplication.objects.filter(leave_type=instance)
        if applications.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                "Cannot delete leave type. There are existing leave applications using this type."
            )
        
        # Remove all balances for this leave type
        LeaveBalance.objects.filter(leave_type=instance).delete()
        
        instance.delete()
    
    @action(detail=True, methods=['get'])
    def policies(self, request, pk=None):
        """Get all policies for a specific leave type"""
        leave_type = self.get_object()
        policies = leave_type.policies.filter(is_active=True)
        serializer = LeaveTypePolicySerializer(policies, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def available_for_user(self, request):
        """Get leave types available for current user"""
        user = request.user
        leave_types = LeaveType.objects.filter(is_active=True)
        
        available_types = []
        for leave_type in leave_types:
            # Check if user has any applicable policy for this leave type
            applicable_policies = leave_type.policies.filter(
                is_active=True,
                effective_from__lte=date.today()
            ).filter(
                Q(effective_to__isnull=True) | Q(effective_to__gte=date.today())
            )
            
            has_applicable_policy = any(
                policy.is_applicable_for_user(user) 
                for policy in applicable_policies
            )
            
            if has_applicable_policy:
                available_types.append(leave_type)
        
        serializer = LeaveTypeSerializer(available_types, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def applicable_policy(self, request, pk=None):
        """Get applicable policy for the current user and this leave type"""
        user = request.user
        leave_type = self.get_object()
        
        # Find applicable policy
        applicable_policies = leave_type.policies.filter(
            is_active=True,
            effective_from__lte=date.today()
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=date.today())
        )
        
        applicable_policy = None
        for policy in applicable_policies:
            if policy.is_applicable_for_user(user):
                applicable_policy = policy
                break
        
        if applicable_policy:
            serializer = LeaveTypePolicySerializer(applicable_policy)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'No applicable policy found for this leave type'},
                status=status.HTTP_404_NOT_FOUND
            )


class LeaveTypePolicyViewSet(viewsets.ModelViewSet):
    """ViewSet for managing leave type policies"""
    queryset = LeaveTypePolicy.objects.all().order_by('-created_at')
    serializer_class = LeaveTypePolicySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        leave_type_id = self.request.query_params.get('leave_type')
        if leave_type_id:
            queryset = queryset.filter(leave_type_id=leave_type_id)
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('-created_at')
    
    def update(self, request, *args, **kwargs):
        """Handle leave policy update with balance management"""
        from common.timezone_utils import get_current_ist_date
        
        partial = kwargs.pop('partial', False)
        policy = self.get_object()
        old_is_active = policy.is_active
        
        serializer = self.get_serializer(policy, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        new_is_active = serializer.validated_data.get('is_active', old_is_active)
        
        # Save the changes first
        updated_policy = serializer.save()
        
        # Track sync status
        auto_synced = False
        sync_count = 0
        current_date = get_current_ist_date()
        
        # Handle balance changes if status changed
        if old_is_active != new_is_active:
            if new_is_active:
                # Policy activated - assign balances
                self._assign_policy_balances(updated_policy)
                auto_synced = True
            else:
                # Policy deactivated - remove balances
                self._remove_policy_balances(updated_policy)
        else:
            # Policy is active and remains active - check if we should auto-sync
            if new_is_active:
                # Only auto-sync if effective_from is today or in the past
                if updated_policy.effective_from <= current_date:
                    sync_count = self._update_existing_balances_with_policy(updated_policy)
                    auto_synced = True
        
        # Return response with sync info
        response_data = serializer.data
        response_data['_sync_info'] = {
            'auto_synced': auto_synced,
            'sync_count': sync_count,
            'effective_from': str(updated_policy.effective_from),
            'is_future_effective': updated_policy.effective_from > current_date if new_is_active else False
        }
        
        return Response(response_data)
    
    def perform_destroy(self, instance):
        """Handle leave policy deletion with balance cleanup"""
        # Remove all balances associated with this policy
        self._remove_policy_balances(instance)
        instance.delete()
    
    def _assign_policy_balances(self, policy):
        """Assign leave balances to users based on the policy"""
        from accounts.models import User
        from datetime import date
        from django.db import transaction
        
        current_year = date.today().year
        
        try:
            with transaction.atomic():
                # Get all active users
                users = User.objects.filter(is_active=True)
                
                created_count = 0
                updated_count = 0
                
                for user in users:
                    # Check if policy is applicable to this user
                    if policy.is_applicable_for_user(user):
                        # Create or update balance
                        balance, created = LeaveBalance.objects.get_or_create(
                            user=user,
                            leave_type=policy.leave_type,
                            year=current_year,
                            defaults={
                                'policy': policy,
                                'opening_balance': policy.annual_quota,
                                'accrued_balance': 0,
                                'used_balance': 0,
                                'carried_forward': 0,
                                'adjustment': 0
                            }
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            # Update existing balance with new policy if it didn't have one
                            if not balance.policy or balance.policy.id != policy.id:
                                balance.policy = policy
                                balance.opening_balance = policy.annual_quota
                                balance.save()
                                updated_count += 1
                
                import logging
                logger = logging.getLogger(__name__)
                logger.info(
                    f"Policy {policy.name} activation: created {created_count} new balances, "
                    f"updated {updated_count} existing balances"
                )
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error assigning balances for policy {policy.name}: {str(e)}")
            raise
    
    def _remove_policy_balances(self, policy):
        """Remove leave balances for users who had this policy assigned"""
        from django.db import transaction
        
        try:
            with transaction.atomic():
                # Find all balances that reference this policy
                balances_to_remove = LeaveBalance.objects.filter(policy=policy)
                
                # Log the removal
                count = balances_to_remove.count()
                if count > 0:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(
                        f"Removing {count} leave balances for policy {policy.name} "
                        f"({policy.leave_type.name})"
                    )
                    
                    # Remove the balances
                    balances_to_remove.delete()
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error removing balances for policy {policy.name}: {str(e)}")
            raise
    
    def _update_existing_balances_with_policy(self, policy):
        """
        Update existing balances to reference the updated policy
        Returns the number of balances updated
        """
        from django.db import transaction
        from common.timezone_utils import get_current_ist_date
        
        updated_count = 0
        
        try:
            with transaction.atomic():
                current_date = get_current_ist_date()
                current_year = current_date.year
                
                # Find all balances for this leave type and year
                # Update ALL balances that currently reference this policy OR
                # balances that should use this policy based on user applicability
                balances = LeaveBalance.objects.filter(
                    leave_type=policy.leave_type,
                    year=current_year
                ).select_related('user', 'policy')
                
                for balance in balances:
                    should_update = False
                    
                    # Update if balance already references this policy (policy was edited)
                    if balance.policy and balance.policy.id == policy.id:
                        should_update = True
                    # Or if this policy is applicable to the user and they don't have a policy
                    elif not balance.policy and policy.is_applicable_for_user(balance.user):
                        should_update = True
                    # Or if this policy is applicable and is the best match for the user
                    elif policy.is_applicable_for_user(balance.user):
                        should_update = True
                    
                    if should_update:
                        # Update the balance to reference the updated policy
                        # This ensures new limits (max_per_month, etc.) apply immediately
                        balance.policy = policy
                        # Don't change opening_balance, used_balance, or accrued_balance
                        # Only update the policy reference so new limits apply
                        balance.save(update_fields=['policy', 'updated_at'])
                        updated_count += 1
                
                import logging
                logger = logging.getLogger(__name__)
                logger.info(
                    f"Synced {updated_count} balances to use policy {policy.name} "
                    f"({policy.leave_type.name}) - max_per_month: {policy.max_per_month}"
                )
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error updating balances for policy {policy.name}: {str(e)}")
            raise
        
        return updated_count
    
    @action(detail=True, methods=['post'])
    def update_user_balances(self, request, pk=None):
        """
        Update user balances after policy changes
        Gives admin control over how to handle existing balances
        """
        policy = self.get_object()
        
        update_mode = request.data.get('update_mode', 'policy_only')  # policy_only, reset_opening, full_reset
        year = request.data.get('year', date.today().year)
        user_ids = request.data.get('user_ids', [])  # Empty = all applicable users
        
        from django.db import transaction
        
        try:
            with transaction.atomic():
                # Get users to update
                if user_ids:
                    users = User.objects.filter(id__in=user_ids, is_active=True)
                else:
                    users = User.objects.filter(is_active=True)
                
                updated_count = 0
                created_count = 0
                skipped_count = 0
                
                for user in users:
                    # Check if policy is applicable to this user
                    if not policy.is_applicable_for_user(user):
                        skipped_count += 1
                        continue
                    
                    # Get or create balance
                    balance, created = LeaveBalance.objects.get_or_create(
                        user=user,
                        leave_type=policy.leave_type,
                        year=year,
                        defaults={
                            'policy': policy,
                            'opening_balance': policy.annual_quota,
                            'accrued_balance': Decimal('0'),
                            'used_balance': Decimal('0'),
                            'carried_forward': Decimal('0'),
                            'adjustment': Decimal('0'),
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        # Update existing balance based on mode
                        if update_mode == 'policy_only':
                            # Only update policy reference, keep all balances intact
                            balance.policy = policy
                            balance.save(update_fields=['policy', 'updated_at'])
                        elif update_mode == 'reset_opening':
                            # Update policy and reset opening balance, keep used/accrued intact
                            balance.policy = policy
                            balance.opening_balance = policy.annual_quota
                            balance.save(update_fields=['policy', 'opening_balance', 'updated_at'])
                        elif update_mode == 'full_reset':
                            # Full reset - WARNING: This resets everything
                            balance.policy = policy
                            balance.opening_balance = policy.annual_quota
                            balance.accrued_balance = Decimal('0')
                            # Keep used_balance and carried_forward intact
                            balance.save(update_fields=['policy', 'opening_balance', 'accrued_balance', 'updated_at'])
                        
                        updated_count += 1
                
                return Response({
                    'message': 'Balances updated successfully',
                    'summary': {
                        'created': created_count,
                        'updated': updated_count,
                        'skipped': skipped_count,
                        'total_processed': created_count + updated_count + skipped_count
                    }
                })
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error updating balances for policy {policy.name}: {str(e)}")
            return Response(
                {'error': f'Failed to update balances: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone a policy with new name"""
        original_policy = self.get_object()
        new_name = request.data.get('name')
        
        if not new_name:
            return Response(
                {'error': 'Name is required for cloning'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create a copy
        cloned_policy = LeaveTypePolicy.objects.create(
            name=new_name,
            leave_type=original_policy.leave_type,
            applicable_gender=original_policy.applicable_gender,
            annual_quota=original_policy.annual_quota,
            accrual_frequency=original_policy.accrual_frequency,
            accrual_rate=original_policy.accrual_rate,
            max_per_week=original_policy.max_per_week,
            max_per_month=original_policy.max_per_month,
            max_per_year=original_policy.max_per_year,
            max_consecutive_days=original_policy.max_consecutive_days,
            min_notice_days=original_policy.min_notice_days,
            requires_approval=original_policy.requires_approval,
            auto_approve_threshold=original_policy.auto_approve_threshold,
            carry_forward_enabled=original_policy.carry_forward_enabled,
            carry_forward_limit=original_policy.carry_forward_limit,
            carry_forward_expiry_months=original_policy.carry_forward_expiry_months,
            min_tenure_days=original_policy.min_tenure_days,
            available_during_probation=original_policy.available_during_probation,
            include_weekends=original_policy.include_weekends,
            include_holidays=original_policy.include_holidays,
            effective_from=date.today()
        )
        
        # Copy applicable roles
        cloned_policy.applicable_roles.set(original_policy.applicable_roles.all())
        
        serializer = self.get_serializer(cloned_policy)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LeaveBalanceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing leave balances"""
    queryset = LeaveBalance.objects.all().order_by('-created_at')
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user if not admin
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        # Filter by query parameters
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        leave_type_id = self.request.query_params.get('leave_type')
        if leave_type_id:
            queryset = queryset.filter(leave_type_id=leave_type_id)
        
        year = self.request.query_params.get('year')
        if year:
            queryset = queryset.filter(year=year)
        else:
            # Default to current year
            queryset = queryset.filter(year=date.today().year)
        
        return queryset.order_by('-year', '-created_at')
    
    @action(detail=False, methods=['get'])
    def my_balances(self, request):
        """Get current user's leave balances"""
        current_year = date.today().year
        balances = LeaveBalance.objects.filter(
            user=request.user,
            year=current_year
        ).select_related('leave_type', 'policy')
        
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Bulk update leave balances"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = BulkLeaveBalanceUpdateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            updated_count = 0
            
            with transaction.atomic():
                for user_id in data['user_ids']:
                    try:
                        user = User.objects.get(id=user_id)
                        balance, created = LeaveBalance.objects.get_or_create(
                            user=user,
                            leave_type=data['leave_type'],
                            year=data['year']
                        )
                        
                        if 'opening_balance' in data:
                            balance.opening_balance = data['opening_balance']
                        if 'adjustment' in data:
                            balance.adjustment = data['adjustment']
                        
                        balance.save()
                        updated_count += 1
                    except User.DoesNotExist:
                        continue
            
            return Response({
                'message': f'Updated {updated_count} leave balances',
                'updated_count': updated_count
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def initialize_for_year(self, request):
        """Initialize leave balances for all users for a specific year"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        year = request.data.get('year', date.today().year)
        
        created_count = 0
        with transaction.atomic():
            users = User.objects.filter(is_active=True, role__isnull=False)
            leave_types = LeaveType.objects.filter(is_active=True)
            
            for user in users:
                for leave_type in leave_types:
                    # Find applicable policy
                    applicable_policies = LeaveTypePolicy.objects.filter(
                        leave_type=leave_type,
                        is_active=True,
                        effective_from__lte=date.today()
                    ).filter(
                        Q(effective_to__isnull=True) | Q(effective_to__gte=date.today())
                    )
                    
                    applicable_policy = None
                    for policy in applicable_policies:
                        if policy.is_applicable_for_user(user):
                            applicable_policy = policy
                            break
                    
                    if applicable_policy:
                        balance, created = LeaveBalance.objects.get_or_create(
                            user=user,
                            leave_type=leave_type,
                            year=year,
                            defaults={
                                'policy': applicable_policy,
                                'opening_balance': applicable_policy.annual_quota
                            }
                        )
                        
                        if created:
                            created_count += 1
        
        return Response({
            'message': f'Initialized {created_count} leave balances for year {year}',
            'created_count': created_count
        })

    @action(detail=False, methods=['post'])
    def assign_balances(self, request):
        """Assign leave balances based on active policies"""
        year = request.data.get('year', date.today().year)
        user_ids = request.data.get('user_ids', [])
        force_reset = request.data.get('force_reset', False)

        try:
            from .services import LeaveBalanceService
            summary = LeaveBalanceService.assign_annual_balances(
                year=year,
                user_ids=user_ids if user_ids else None,
                force_reset=force_reset
            )

            return Response({
                'message': 'Leave balances assigned successfully',
                'summary': summary
            })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get comprehensive balance summary for a specific user"""
        try:
            user = User.objects.get(pk=pk)
            year = request.query_params.get('year', date.today().year)

            from .services import LeaveReportService
            summary = LeaveReportService.get_user_leave_summary(user, year)

            return Response(summary)

        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def summaries(self, request):
        """Get balance summaries for all users"""
        try:
            year = request.query_params.get('year', date.today().year)
            user_ids = request.query_params.getlist('user_ids')

            if user_ids:
                users = User.objects.filter(id__in=user_ids, is_active=True)
            else:
                users = User.objects.filter(is_active=True)

            summaries = []
            from .services import LeaveReportService
            for user in users:
                summary = LeaveReportService.get_user_leave_summary(user, year)
                summaries.append(summary)

            return Response(summaries)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def sync_policy_rules(self, request):
        """
        Sync all balances with their current applicable policies.
        This updates the policy reference for each balance without changing balance amounts.
        """
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        year = request.data.get('year', date.today().year)
        
        try:
            from django.db.models import Q
            
            # Get all active policies
            active_policies = LeaveTypePolicy.objects.filter(
                is_active=True,
                effective_from__lte=date.today()
            ).filter(
                Q(effective_to__isnull=True) | Q(effective_to__gte=date.today())
            ).select_related('leave_type')
            
            # Get all balances for the year
            balances = LeaveBalance.objects.filter(year=year).select_related('user', 'leave_type', 'policy')
            
            updated_count = 0
            skipped_count = 0
            
            with transaction.atomic():
                for balance in balances:
                    # Find the applicable policy for this user and leave type
                    applicable_policy = None
                    for policy in active_policies:
                        if policy.leave_type_id == balance.leave_type_id and policy.is_applicable_for_user(balance.user):
                            applicable_policy = policy
                            break
                    
                    if applicable_policy:
                        # Update balance to reference the current policy
                        if balance.policy_id != applicable_policy.id:
                            balance.policy = applicable_policy
                            balance.save(update_fields=['policy', 'updated_at'])
                            updated_count += 1
                        else:
                            skipped_count += 1
                    else:
                        skipped_count += 1
            
            return Response({
                'message': f'Synced policy rules for {updated_count} balances',
                'summary': {
                    'updated': updated_count,
                    'skipped': skipped_count,
                    'total': updated_count + skipped_count
                }
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error syncing policy rules: {str(e)}")
            return Response(
                {'error': f'Failed to sync policy rules: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LeaveApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing leave applications"""
    queryset = LeaveApplication.objects.all().order_by('-applied_at')
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return LeaveApplicationCreateSerializer
        return LeaveApplicationSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user if not admin
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)
        
        # Filter by leave type
        leave_type_id = self.request.query_params.get('leave_type')
        if leave_type_id:
            queryset = queryset.filter(leave_type_id=leave_type_id)
        
        # Filter by user (admin only)
        if self.request.user.is_staff:
            user_id = self.request.query_params.get('user')
            if user_id:
                queryset = queryset.filter(user_id=user_id)
        
        return queryset.select_related('user', 'leave_type', 'policy', 'approved_by').order_by('-applied_at')
    
    def perform_create(self, serializer):
        # Validate dates before saving
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')
        
        # Import timezone utilities for proper date validation
        from common.timezone_utils import get_current_ist_date
        from rest_framework.exceptions import ValidationError
        
        current_date = get_current_ist_date()
        
        # Check if start date is in the past
        if start_date < current_date:
            raise ValidationError({
                'start_date': 'Leave start date cannot be in the past. Please select a future date.'
            })
        
        # Check if end date is before start date
        if end_date < start_date:
            raise ValidationError({
                'end_date': 'Leave end date cannot be before the start date.'
            })
        
        # Check if dates are too far in the future (business rule)
        from datetime import timedelta
        max_future_date = current_date + timedelta(days=365)  # 1 year ahead
        
        if start_date > max_future_date:
            raise ValidationError({
                'start_date': 'Leave start date cannot be more than 1 year in the future.'
            })
        
        # Save the application with auto-approval logic
        application = serializer.save(user=self.request.user)
        
        # Check for auto-approval after saving (backup logic)
        if application.policy and not application.policy.requires_approval and application.status == 'pending':
            application.status = 'approved'
            application.approved_at = timezone.now()
            application.save()
            
            # Send notification about auto-approval if needed
            # You can add notification logic here
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a leave application"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        application = self.get_object()
        
        # Check if application dates are in the past
        from common.timezone_utils import get_current_ist_date
        current_date = get_current_ist_date()
        
        if application.start_date < current_date:
            return Response(
                {'error': 'Cannot approve leave application as the start date has already passed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = LeaveApplicationApprovalSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            try:
                if data['action'] == 'approve':
                    application.approve(request.user, data.get('comments'))
                    return Response({'message': 'Application approved successfully'})
                else:
                    application.reject(
                        request.user, 
                        data['rejection_reason'],
                        data.get('comments')
                    )
                    return Response({'message': 'Application rejected successfully'})
            except Exception as e:
                return Response(
                    {'error': f'Failed to process application: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a leave application"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        application = self.get_object()
        
        rejection_reason = request.data.get('rejection_reason', '')
        comments = request.data.get('comments', '')
        
        if not rejection_reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            application.reject(request.user, rejection_reason, comments)
            return Response({'message': 'Application rejected successfully'})
        except Exception as e:
            return Response(
                {'error': f'Failed to reject application: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a leave application"""
        application = self.get_object()
        
        # Check permission
        if application.user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not application.can_be_cancelled():
            # Provide more specific error messages
            if application.start_date < date.today():
                return Response(
                    {'error': 'Cannot cancel leave request as the start date has already passed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif application.status not in ['draft', 'pending', 'approved']:
                return Response(
                    {'error': f'Cannot cancel leave request with status: {application.status}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                return Response(
                    {'error': 'Application cannot be cancelled'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Use the new cancel method that handles balance restoration
        application.cancel(cancelled_by=request.user)
        
        return Response({'message': 'Application cancelled successfully'})
    
    def destroy(self, request, *args, **kwargs):
        """Delete a leave application with proper permissions"""
        application = self.get_object()
        
        # Check permissions based on user type
        if request.user.is_staff:
            # Admin can delete until end date
            if not application.can_be_deleted_by_admin():
                return Response(
                    {'error': 'Cannot delete this application. Either it has ended or is already rejected/cancelled.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Regular user can only delete their own applications until start date
            if application.user != request.user:
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if not application.can_be_deleted_by_user():
                return Response(
                    {'error': 'Cannot delete this application. You can only delete pending applications before the start date.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # If application was approved, restore the balance
        if application.status == 'approved':
            try:
                balance = LeaveBalance.objects.get(
                    user=application.user,
                    leave_type=application.leave_type,
                    year=application.start_date.year
                )
                balance.used_balance = max(Decimal('0'), balance.used_balance - application.total_days)
                balance.save()
            except LeaveBalance.DoesNotExist:
                pass
        
        # Delete the application
        application.delete()
        
        return Response({'message': 'Leave application deleted successfully'})
    
    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        """Get comments for a leave application"""
        application = self.get_object()
        
        # Check permission
        if application.user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        comments = application.comments.all()
        if not request.user.is_staff:
            # Hide internal comments from employees
            comments = comments.filter(is_internal=False)
        
        serializer = LeaveApplicationCommentSerializer(comments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        """Add a comment to leave application"""
        application = self.get_object()
        
        # Check permission
        if application.user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = LeaveApplicationCommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(application=application, user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Get pending applications for approval (admin only)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        applications = LeaveApplication.objects.filter(
            status='pending'
        ).select_related('user', 'leave_type', 'policy').order_by('applied_at')
        
        serializer = LeaveApplicationSerializer(applications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_applications(self, request):
        """Get current user's leave applications"""
        applications = LeaveApplication.objects.filter(
            user=request.user
        ).select_related('leave_type', 'policy', 'approved_by').order_by('-applied_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            applications = applications.filter(status=status_filter)
        
        serializer = LeaveApplicationSerializer(applications, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leave_calendar(request):
    """Get leave calendar data"""
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    if not start_date or not end_date:
        return Response(
            {'error': 'start_date and end_date parameters are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    calendar_entries = LeaveCalendar.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).select_related('user', 'leave_application__leave_type')
    
    # Filter by user if not admin
    if not request.user.is_staff:
        calendar_entries = calendar_entries.filter(user=request.user)
    
    serializer = LeaveCalendarSerializer(calendar_entries, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leave_statistics(request):
    """Get leave statistics"""
    if not request.user.is_staff:
        # Employee can only see their own stats
        user = request.user
        current_year = date.today().year
        
        balances = LeaveBalance.objects.filter(
            user=user,
            year=current_year
        ).select_related('leave_type')
        
        stats = []
        for balance in balances:
            pending_apps = LeaveApplication.objects.filter(
                user=user,
                leave_type=balance.leave_type,
                status='pending',
                start_date__year=current_year
            ).count()
            
            stats.append({
                'user_id': user.id,
                'user_name': user.get_full_name(),
                'leave_type': balance.leave_type.name,
                'leave_type_code': balance.leave_type.code,
                'total_available': balance.total_available,
                'used_balance': balance.used_balance,
                'remaining_balance': balance.remaining_balance,
                'pending_applications': pending_apps
            })
        
        return Response(stats)
    
    else:
        # Admin can see overall statistics
        year = request.query_params.get('year', date.today().year)
        
        # Overall stats
        total_applications = LeaveApplication.objects.filter(
            start_date__year=year
        ).count()
        
        approved_applications = LeaveApplication.objects.filter(
            start_date__year=year,
            status='approved'
        ).count()
        
        rejected_applications = LeaveApplication.objects.filter(
            start_date__year=year,
            status='rejected'
        ).count()
        
        pending_applications = LeaveApplication.objects.filter(
            status='pending'
        ).count()
        
        total_days_taken = LeaveApplication.objects.filter(
            start_date__year=year,
            status='approved'
        ).aggregate(total=Sum('total_days'))['total'] or 0
        
        # By leave type
        by_leave_type = LeaveApplication.objects.filter(
            start_date__year=year
        ).values('leave_type__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # By role
        by_role = LeaveApplication.objects.filter(
            start_date__year=year
        ).values('user__role__display_name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        stats = {
            'period': str(year),
            'total_applications': total_applications,
            'approved_applications': approved_applications,
            'rejected_applications': rejected_applications,
            'pending_applications': pending_applications,
            'total_days_taken': total_days_taken,
            'by_leave_type': {item['leave_type__name']: item['count'] for item in by_leave_type},
            'by_role': {item['user__role__display_name']: item['count'] for item in by_role if item['user__role__display_name']}
        }
        
        return Response(stats)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_annual_balances(request):
    """API endpoint to assign annual leave balances"""
    if not request.user.is_staff:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    from .services import LeaveBalanceService
    
    year = request.data.get('year', date.today().year)
    user_ids = request.data.get('user_ids', None)
    force_reset = request.data.get('force_reset', False)
    
    try:
        summary = LeaveBalanceService.assign_annual_balances(
            year=year,
            user_ids=user_ids,
            force_reset=force_reset
        )
        return Response(summary)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_monthly_accruals(request):
    """API endpoint to process monthly accruals"""
    if not request.user.is_staff:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    from .services import LeaveBalanceService
    
    year = request.data.get('year', date.today().year)
    month = request.data.get('month', date.today().month)
    user_ids = request.data.get('user_ids', None)
    
    try:
        summary = LeaveBalanceService.process_monthly_accruals(
            year=year,
            month=month,
            user_ids=user_ids
        )
        return Response(summary)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def adjust_balance(request):
    """API endpoint to manually adjust leave balance"""
    if not request.user.is_staff:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    from .services import LeaveBalanceService
    from .models import LeaveType
    
    try:
        user_id = request.data.get('user_id')
        leave_type_id = request.data.get('leave_type_id')
        year = request.data.get('year', date.today().year)
        adjustment_amount = Decimal(str(request.data.get('adjustment_amount', 0)))
        reason = request.data.get('reason', '')
        
        if not user_id or not leave_type_id or adjustment_amount == 0:
            return Response(
                {'error': 'user_id, leave_type_id, and adjustment_amount are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = User.objects.get(id=user_id)
        leave_type = LeaveType.objects.get(id=leave_type_id)
        
        balance = LeaveBalanceService.adjust_balance(
            user=user,
            leave_type=leave_type,
            year=year,
            adjustment_amount=adjustment_amount,
            reason=reason,
            performed_by=request.user
        )
        
        serializer = LeaveBalanceSerializer(balance)
        return Response({
            'message': 'Balance adjusted successfully',
            'balance': serializer.data
        })
        
    except (User.DoesNotExist, LeaveType.DoesNotExist) as e:
        return Response(
            {'error': f'Invalid user or leave type: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_balance_summary(request, user_id=None):
    """Get comprehensive balance summary for a user"""
    if user_id:
        if not request.user.is_staff and request.user.id != int(user_id):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        user = User.objects.get(id=user_id)
    else:
        user = request.user
    
    from .services import LeaveBalanceService
    
    year = request.query_params.get('year')
    if year:
        year = int(year)
    
    try:
        summary = LeaveBalanceService.get_balance_summary_for_user(user, year)
        return Response(summary)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_leave_eligibility(request):
    """Check if user can apply for leave"""
    from .services import LeaveBalanceService
    from .models import LeaveType
    
    try:
        leave_type_id = request.data.get('leave_type_id')
        days = request.data.get('days')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        if not all([leave_type_id, days, start_date, end_date]):
            return Response(
                {'error': 'leave_type_id, days, start_date, and end_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        leave_type = LeaveType.objects.get(id=leave_type_id)
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        is_eligible, messages = LeaveBalanceService.check_leave_eligibility(
            user=request.user,
            leave_type=leave_type,
            days=float(days),
            start_date=start_date,
            end_date=end_date
        )
        
        return Response({
            'is_eligible': is_eligible,
            'messages': messages
        })
        
    except (LeaveType.DoesNotExist, ValueError) as e:
        return Response(
            {'error': f'Invalid data: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def balance_report(request):
    """Generate balance report"""
    if not request.user.is_staff:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    from .services import LeaveReportService
    
    year = request.query_params.get('year')
    if year:
        year = int(year)
    
    department = request.query_params.get('department')
    role = request.query_params.get('role')
    
    try:
        report_data = LeaveReportService.generate_balance_report(
            department=department,
            role=role,
            year=year
        )
        return Response(report_data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def compliance_report(request):
    """Generate policy compliance report"""
    if not request.user.is_staff:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    from .services import LeaveReportService
    
    year = request.query_params.get('year')
    if year:
        year = int(year)
    
    try:
        report_data = LeaveReportService.generate_policy_compliance_report(year=year)
        return Response(report_data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_balance_import(request):
    """Bulk import/update leave balances"""
    if not request.user.is_staff:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    from .services import LeaveBalanceService
    
    balance_data = request.data.get('balance_data', [])
    
    if not balance_data:
        return Response(
            {'error': 'balance_data is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        summary = LeaveBalanceService.bulk_balance_import(
            balance_data=balance_data,
            performed_by=request.user
        )
        return Response(summary)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def test_view(request):
    return Response({'message': 'Leave app is working!'}, status=status.HTTP_200_OK)


