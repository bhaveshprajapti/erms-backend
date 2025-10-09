from django.db import transaction, models
from django.utils import timezone
from decimal import Decimal
from datetime import date, datetime, timedelta
from accounts.models import User
from .models import (
    LeaveType, LeaveTypePolicy, LeaveBalance, OverallLeavePolicy,
    LeaveBalanceAudit, LeaveBlackoutDate, LeaveApplication
)
import logging

logger = logging.getLogger(__name__)

class LeaveBalanceService:
    """Service class for managing leave balances"""
    
    @classmethod
    @transaction.atomic
    def assign_annual_balances(cls, year=None, user_ids=None, force_reset=False):
        """
        Assign annual leave balances to all active users based on applicable policies
        
        Args:
            year (int): Year to assign balances for (default: current year)
            user_ids (list): Specific user IDs to assign balances for (default: all active users)
            force_reset (bool): Whether to reset existing balances (default: False)
            
        Returns:
            dict: Summary of balance assignments
        """
        if year is None:
            year = date.today().year
            
        if user_ids:
            users = User.objects.filter(id__in=user_ids, is_active=True)
        else:
            users = User.objects.filter(is_active=True)
            
        summary = {
            'total_users': 0,
            'balances_created': 0,
            'balances_updated': 0,
            'balances_skipped': 0,
            'errors': []
        }
        
        for user in users:
            summary['total_users'] += 1
            try:
                user_summary = cls._assign_user_annual_balances(user, year, force_reset)
                summary['balances_created'] += user_summary['created']
                summary['balances_updated'] += user_summary['updated']
                summary['balances_skipped'] += user_summary['skipped']
            except Exception as e:
                error_msg = f"Error assigning balances to {user.username}: {str(e)}"
                logger.error(error_msg)
                summary['errors'].append(error_msg)
                
        return summary
    
    @classmethod
    @transaction.atomic
    def _assign_user_annual_balances(cls, user, year, force_reset=False):
        """Assign annual balances for a specific user"""
        summary = {'created': 0, 'updated': 0, 'skipped': 0}
        
        # Get all active leave types and their applicable policies
        leave_types = LeaveType.objects.filter(is_active=True)
        
        for leave_type in leave_types:
            # Find applicable policy for this user and leave type
            applicable_policy = cls._get_applicable_policy_for_user(user, leave_type, year)
            
            if not applicable_policy:
                summary['skipped'] += 1
                continue
                
            # Get or create balance record
            balance, created = LeaveBalance.objects.get_or_create(
                user=user,
                leave_type=leave_type,
                year=year,
                defaults={
                    'policy': applicable_policy,
                    'opening_balance': applicable_policy.annual_quota,
                    'accrued_balance': Decimal('0'),
                    'used_balance': Decimal('0'),
                    'carried_forward': Decimal('0'),
                    'adjustment': Decimal('0'),
                    'last_reset_date': date.today(),
                }
            )
            
            if created:
                summary['created'] += 1
                # Create audit record
                LeaveBalanceAudit.objects.create(
                    balance=balance,
                    action='annual_reset',
                    old_balance=Decimal('0'),
                    new_balance=applicable_policy.annual_quota,
                    change_amount=applicable_policy.annual_quota,
                    reason=f'Annual balance assignment for {year}',
                    performed_by=None  # System action
                )
            else:
                if force_reset:
                    old_balance = balance.opening_balance
                    # Calculate carry forward if policy allows
                    carry_forward = cls._calculate_carry_forward(balance, applicable_policy)
                    
                    balance.opening_balance = applicable_policy.annual_quota
                    balance.accrued_balance = Decimal('0')
                    balance.used_balance = Decimal('0')
                    balance.carried_forward = carry_forward
                    balance.policy = applicable_policy
                    balance.last_reset_date = date.today()
                    balance.save()
                    
                    summary['updated'] += 1
                    
                    # Create audit record
                    LeaveBalanceAudit.objects.create(
                        balance=balance,
                        action='annual_reset',
                        old_balance=old_balance,
                        new_balance=balance.opening_balance + carry_forward,
                        change_amount=balance.opening_balance + carry_forward - old_balance,
                        reason=f'Annual balance reset for {year} with carry forward',
                        performed_by=None
                    )
                else:
                    summary['skipped'] += 1
                    
        return summary
    
    @classmethod
    def _get_applicable_policy_for_user(cls, user, leave_type, year):
        """Get the most applicable policy for a user and leave type"""
        policies = LeaveTypePolicy.objects.filter(
            leave_type=leave_type,
            is_active=True,
            effective_from__lte=date(year, 12, 31)
        ).filter(
            models.Q(effective_to__isnull=True) | 
            models.Q(effective_to__gte=date(year, 1, 1))
        )
        
        for policy in policies:
            if policy.is_applicable_for_user(user):
                return policy
                
        return None
    
    @classmethod
    def _calculate_carry_forward(cls, balance, policy):
        """Calculate carry forward amount based on policy"""
        if not policy.carry_forward_enabled:
            return Decimal('0')
            
        carry_forward_amount = balance.remaining_balance
        
        # Apply carry forward limit
        if policy.carry_forward_limit > 0:
            carry_forward_amount = min(carry_forward_amount, policy.carry_forward_limit)
            
        return max(carry_forward_amount, Decimal('0'))
    
    @classmethod
    @transaction.atomic
    def process_monthly_accruals(cls, year=None, month=None, user_ids=None):
        """Process monthly accruals for all users"""
        if year is None:
            year = date.today().year
        if month is None:
            month = date.today().month
            
        if user_ids:
            balances = LeaveBalance.objects.filter(
                user_id__in=user_ids,
                year=year,
                policy__accrual_frequency='monthly'
            ).select_related('user', 'leave_type', 'policy')
        else:
            balances = LeaveBalance.objects.filter(
                year=year,
                policy__accrual_frequency='monthly'
            ).select_related('user', 'leave_type', 'policy')
            
        summary = {'processed': 0, 'skipped': 0, 'errors': []}
        
        for balance in balances:
            try:
                # Check if accrual already processed for this month
                current_month_date = date(year, month, 1)
                if balance.last_accrual_date and balance.last_accrual_date >= current_month_date:
                    summary['skipped'] += 1
                    continue
                    
                if balance.policy and balance.policy.accrual_rate > 0:
                    old_accrued = balance.accrued_balance
                    balance.accrued_balance += balance.policy.accrual_rate
                    balance.last_accrual_date = current_month_date
                    balance.save()
                    
                    # Create audit record
                    LeaveBalanceAudit.objects.create(
                        balance=balance,
                        action='accrual',
                        old_balance=old_accrued,
                        new_balance=balance.accrued_balance,
                        change_amount=balance.policy.accrual_rate,
                        reason=f'Monthly accrual for {year}-{month:02d}',
                        performed_by=None
                    )
                    
                    summary['processed'] += 1
                else:
                    summary['skipped'] += 1
                    
            except Exception as e:
                error_msg = f"Error processing accrual for {balance}: {str(e)}"
                logger.error(error_msg)
                summary['errors'].append(error_msg)
                
        return summary
    
    @classmethod
    @transaction.atomic
    def adjust_balance(cls, user, leave_type, year, adjustment_amount, reason, performed_by=None):
        """Manually adjust a user's leave balance"""
        balance = LeaveBalance.objects.get(
            user=user,
            leave_type=leave_type,
            year=year
        )
        
        old_adjustment = balance.adjustment
        balance.adjustment += adjustment_amount
        balance.save()
        
        # Create audit record
        LeaveBalanceAudit.objects.create(
            balance=balance,
            action='manual_adjustment',
            old_balance=old_adjustment,
            new_balance=balance.adjustment,
            change_amount=adjustment_amount,
            reason=reason,
            performed_by=performed_by
        )
        
        return balance
    
    @classmethod
    def get_balance_summary_for_user(cls, user, year=None):
        """Get comprehensive balance summary for a user"""
        if year is None:
            year = date.today().year
            
        balances = LeaveBalance.objects.filter(
            user=user,
            year=year
        ).select_related('leave_type', 'policy')
        
        summary = {
            'year': year,
            'balances': [],
            'total_available': Decimal('0'),
            'total_used': Decimal('0'),
            'total_remaining': Decimal('0'),
        }
        
        for balance in balances:
            balance_info = {
                'leave_type': balance.leave_type.name,
                'leave_type_code': balance.leave_type.code,
                'opening_balance': balance.opening_balance,
                'accrued_balance': balance.accrued_balance,
                'carried_forward': balance.carried_forward,
                'adjustment': balance.adjustment,
                'total_available': balance.total_available,
                'used_balance': balance.used_balance,
                'remaining_balance': balance.remaining_balance,
                'pending_balance': balance.pending_balance,
                'policy_name': balance.policy.name if balance.policy else None,
            }
            
            summary['balances'].append(balance_info)
            summary['total_available'] += balance.total_available
            summary['total_used'] += balance.used_balance
            summary['total_remaining'] += balance.remaining_balance
            
        return summary
    
    @classmethod
    def check_leave_eligibility(cls, user, leave_type, days, start_date, end_date):
        """
        Comprehensive eligibility check for leave application
        
        Returns:
            tuple: (is_eligible, messages_list)
        """
        messages = []
        is_eligible = True
        
        try:
            balance = LeaveBalance.objects.get(
                user=user,
                leave_type=leave_type,
                year=start_date.year
            )
            
            can_apply, message = balance.can_apply_for_days(days, start_date, end_date)
            if not can_apply:
                is_eligible = False
                messages.append(message)
                
        except LeaveBalance.DoesNotExist:
            is_eligible = False
            messages.append(f"No leave balance found for {leave_type.name} in {start_date.year}")
            
        # Additional checks can be added here
        # - Team/department simultaneous leave limits
        # - Minimum gap between leaves
        # - Weekend/holiday restrictions
        
        return is_eligible, messages
    
    @classmethod
    @transaction.atomic
    def bulk_balance_import(cls, balance_data, performed_by=None):
        """
        Bulk import/update leave balances
        
        Args:
            balance_data: List of dictionaries with balance information
            performed_by: User performing the import
            
        Returns:
            dict: Import summary
        """
        summary = {'created': 0, 'updated': 0, 'errors': []}
        
        for data in balance_data:
            try:
                user = User.objects.get(username=data['username'])
                leave_type = LeaveType.objects.get(code=data['leave_type_code'])
                year = data['year']
                
                balance, created = LeaveBalance.objects.get_or_create(
                    user=user,
                    leave_type=leave_type,
                    year=year,
                    defaults={
                        'opening_balance': data.get('opening_balance', 0),
                        'accrued_balance': data.get('accrued_balance', 0),
                        'used_balance': data.get('used_balance', 0),
                        'carried_forward': data.get('carried_forward', 0),
                        'adjustment': data.get('adjustment', 0),
                    }
                )
                
                if created:
                    summary['created'] += 1
                else:
                    # Update existing balance
                    old_total = balance.total_available
                    balance.opening_balance = data.get('opening_balance', balance.opening_balance)
                    balance.accrued_balance = data.get('accrued_balance', balance.accrued_balance)
                    balance.used_balance = data.get('used_balance', balance.used_balance)
                    balance.carried_forward = data.get('carried_forward', balance.carried_forward)
                    balance.adjustment = data.get('adjustment', balance.adjustment)
                    balance.save()
                    
                    summary['updated'] += 1
                    
                    # Create audit record
                    LeaveBalanceAudit.objects.create(
                        balance=balance,
                        action='correction',
                        old_balance=old_total,
                        new_balance=balance.total_available,
                        change_amount=balance.total_available - old_total,
                        reason='Bulk import/update',
                        performed_by=performed_by
                    )
                    
            except Exception as e:
                error_msg = f"Error importing balance for {data.get('username', 'unknown')}: {str(e)}"
                logger.error(error_msg)
                summary['errors'].append(error_msg)
                
        return summary


class LeaveReportService:
    """Service for generating leave reports"""
    
    @classmethod
    def generate_balance_report(cls, department=None, role=None, year=None):
        """Generate comprehensive balance report"""
        if year is None:
            year = date.today().year
            
        filters = {'year': year, 'user__is_active': True}
        
        if department:
            filters['user__department'] = department
        if role:
            filters['user__role'] = role
            
        balances = LeaveBalance.objects.filter(**filters).select_related(
            'user', 'leave_type', 'policy'
        ).order_by('user__username', 'leave_type__name')
        
        report_data = []
        for balance in balances:
            report_data.append({
                'employee_id': balance.user.employee_id,
                'username': balance.user.username,
                'full_name': balance.user.get_full_name(),
                'department': balance.user.department.name if hasattr(balance.user, 'department') else '',
                'role': balance.user.role.name if balance.user.role else '',
                'leave_type': balance.leave_type.name,
                'opening_balance': float(balance.opening_balance),
                'accrued_balance': float(balance.accrued_balance),
                'carried_forward': float(balance.carried_forward),
                'adjustment': float(balance.adjustment),
                'total_available': float(balance.total_available),
                'used_balance': float(balance.used_balance),
                'remaining_balance': float(balance.remaining_balance),
                'last_accrual_date': balance.last_accrual_date,
                'last_reset_date': balance.last_reset_date,
            })
            
        return report_data
    
    @classmethod
    def generate_policy_compliance_report(cls, year=None):
        """Generate report showing policy compliance"""
        if year is None:
            year = date.today().year
            
        policies = LeaveTypePolicy.objects.filter(is_active=True)
        users_without_balances = []
        policy_violations = []
        
        for policy in policies:
            # Check users who should have this policy but don't have balances
            applicable_users = User.objects.filter(is_active=True)
            for user in applicable_users:
                if policy.is_applicable_for_user(user):
                    try:
                        balance = LeaveBalance.objects.get(
                            user=user,
                            leave_type=policy.leave_type,
                            year=year
                        )
                        # Check for policy violations
                        if balance.policy != policy:
                            policy_violations.append({
                                'user': user.username,
                                'leave_type': policy.leave_type.name,
                                'expected_policy': policy.name,
                                'actual_policy': balance.policy.name if balance.policy else 'None'
                            })
                    except LeaveBalance.DoesNotExist:
                        users_without_balances.append({
                            'user': user.username,
                            'leave_type': policy.leave_type.name,
                            'expected_policy': policy.name,
                            'role': user.role.name if user.role else 'No Role'
                        })
        
        return {
            'users_without_balances': users_without_balances,
            'policy_violations': policy_violations
        }

    @classmethod
    def check_overall_leave_limits(cls, user, days, start_date, end_date):
        """
        Check if leave application complies with overall leave policy limits

        Returns:
            tuple: (is_allowed, messages_list)
        """
        messages = []
        is_allowed = True

        # Get all applicable overall policies
        overall_policies = OverallLeavePolicy.objects.filter(is_active=True)

        for policy in overall_policies:
            if not policy.is_applicable_for_user(user):
                continue

            # Check total per week limit
            if policy.max_total_per_week and start_date:
                week_start = start_date - timedelta(days=start_date.weekday())
                week_end = week_start + timedelta(days=6)

                # Get total leave days in this week across all leave types
                total_week_used = LeaveApplication.objects.filter(
                    user=user,
                    status__in=['approved', 'pending'],
                    start_date__gte=week_start,
                    end_date__lte=week_end
                ).aggregate(total=models.Sum('total_days'))['total'] or 0

                if total_week_used + days > policy.max_total_per_week:
                    is_allowed = False
                    messages.append(
                        f"Overall weekly limit exceeded. "
                        f"Limit: {policy.max_total_per_week} days, "
                        f"Used: {total_week_used} days, "
                        f"Requested: {days} days"
                    )

            # Check total per month limit
            if policy.max_total_per_month and start_date:
                # Get total leave days in this month across all leave types
                total_month_used = LeaveApplication.objects.filter(
                    user=user,
                    status__in=['approved', 'pending'],
                    start_date__year=start_date.year,
                    start_date__month=start_date.month
                ).aggregate(total=models.Sum('total_days'))['total'] or 0

                if total_month_used + days > policy.max_total_per_month:
                    is_allowed = False
                    messages.append(
                        f"Overall monthly limit exceeded. "
                        f"Limit: {policy.max_total_per_month} days, "
                        f"Used: {total_month_used} days, "
                        f"Requested: {days} days"
                    )

            # Check total per year limit
            if policy.max_total_per_year and start_date:
                # Get total leave days in this year across all leave types
                total_year_used = LeaveApplication.objects.filter(
                    user=user,
                    status__in=['approved', 'pending'],
                    start_date__year=start_date.year
                ).aggregate(total=models.Sum('total_days'))['total'] or 0

                if total_year_used + days > policy.max_total_per_year:
                    is_allowed = False
                    messages.append(
                        f"Overall yearly limit exceeded. "
                        f"Limit: {policy.max_total_per_year} days, "
                        f"Used: {total_year_used} days, "
                        f"Requested: {days} days"
                    )

            # Check consecutive days limit
            if policy.max_total_consecutive_days and start_date and end_date:
                consecutive_days = (end_date - start_date).days + 1
                if consecutive_days > policy.max_total_consecutive_days:
                    is_allowed = False
                    messages.append(
                        f"Consecutive days limit exceeded. "
                        f"Maximum: {policy.max_total_consecutive_days} days, "
                        f"Requested: {consecutive_days} days"
                    )

            # Check minimum gap between leaves
            if policy.min_gap_between_leaves > 0 and start_date:
                # Find the most recent leave application
                last_leave = LeaveApplication.objects.filter(
                    user=user,
                    status__in=['approved', 'pending'],
                    end_date__lt=start_date
                ).order_by('-end_date').first()

                if last_leave:
                    days_gap = (start_date - last_leave.end_date).days
                    if days_gap < policy.min_gap_between_leaves:
                        is_allowed = False
                        messages.append(
                            f"Minimum gap between leaves not met. "
                            f"Required: {policy.min_gap_between_leaves} days, "
                            f"Available: {days_gap} days"
                        )

        return is_allowed, messages

    @classmethod
    def get_user_leave_summary(cls, user, year=None):
        """
        Get comprehensive leave summary for a user including overall policy compliance

        Returns:
            dict: Comprehensive leave summary
        """
        if year is None:
            year = date.today().year

        # Get all leave balances for the user
        balances = LeaveBalance.objects.filter(
            user=user,
            year=year
        ).select_related('leave_type', 'policy')

        # Get all leave applications for the year
        applications = LeaveApplication.objects.filter(
            user=user,
            start_date__year=year
        ).select_related('leave_type', 'policy')

        # Calculate totals
        total_allocated = sum(balance.total_available for balance in balances)
        total_used = sum(balance.used_balance for balance in balances)
        total_pending = sum(app.total_days for app in applications.filter(status='pending'))

        # Check overall policy compliance
        overall_compliance = cls.check_overall_policy_compliance(user, year)

        summary = {
            'year': year,
            'user': user.username,
            'total_allocated': float(total_allocated),
            'total_used': float(total_used),
            'total_pending': float(total_pending),
            'total_remaining': float(total_allocated - total_used - total_pending),
            'balances': [],
            'applications': [],
            'overall_compliance': overall_compliance
        }

        # Add balance details
        for balance in balances:
            summary['balances'].append({
                'leave_type': balance.leave_type.name,
                'leave_type_code': balance.leave_type.code,
                'allocated': float(balance.total_available),
                'used': float(balance.used_balance),
                'pending': float(balance.pending_balance - balance.remaining_balance),
                'remaining': float(balance.remaining_balance),
                'policy_name': balance.policy.name if balance.policy else 'No Policy'
            })

        # Add application details
        for app in applications:
            summary['applications'].append({
                'leave_type': app.leave_type.name,
                'start_date': app.start_date,
                'end_date': app.end_date,
                'days': float(app.total_days),
                'status': app.status,
                'policy_name': app.policy.name if app.policy else 'No Policy'
            })

        return summary

    @classmethod
    def check_overall_policy_compliance(cls, user, year=None):
        """
        Check user's compliance with overall leave policies

        Returns:
            dict: Compliance status and violations
        """
        if year is None:
            year = date.today().year

        compliance = {
            'compliant': True,
            'violations': [],
            'warnings': []
        }

        # Get all applicable overall policies
        policies = OverallLeavePolicy.objects.filter(is_active=True)

        for policy in policies:
            if not policy.is_applicable_for_user(user):
                continue

            # Check current year usage against policy limits
            current_usage = LeaveApplication.objects.filter(
                user=user,
                status__in=['approved', 'pending'],
                start_date__year=year
            ).aggregate(
                total_weekly=models.Sum('total_days', filter=models.Q(
                    start_date__gte=date.today() - timedelta(days=date.today().weekday())
                )),
                total_monthly=models.Sum('total_days', filter=models.Q(
                    start_date__year=year,
                    start_date__month=date.today().month
                )),
                total_yearly=models.Sum('total_days')
            )

            # Check weekly limit
            if policy.max_total_per_week and current_usage['total_weekly']:
                if current_usage['total_weekly'] > policy.max_total_per_week:
                    compliance['violations'].append(
                        f"Weekly limit exceeded: {current_usage['total_weekly']}/{policy.max_total_per_week} days"
                    )
                    compliance['compliant'] = False

            # Check monthly limit
            if policy.max_total_per_month and current_usage['total_monthly']:
                if current_usage['total_monthly'] > policy.max_total_per_month:
                    compliance['violations'].append(
                        f"Monthly limit exceeded: {current_usage['total_monthly']}/{policy.max_total_per_month} days"
                    )
                    compliance['compliant'] = False

            # Check yearly limit
            if policy.max_total_per_year and current_usage['total_yearly']:
                if current_usage['total_yearly'] > policy.max_total_per_year:
                    compliance['violations'].append(
                        f"Yearly limit exceeded: {current_usage['total_yearly']}/{policy.max_total_per_year} days"
                    )
                    compliance['compliant'] = False

        return compliance