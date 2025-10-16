from django.db.models.signals import post_save, post_migrate, pre_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import date
from django.db import transaction
from accounts.models import User
from .models import LeaveTypePolicy, LeaveBalance, LeaveType, LeaveApplication
from .services import LeaveBalanceService
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def assign_leave_balances_for_new_user(sender, instance, created, **kwargs):
    """
    Automatically assign leave balances for new users based on active policies
    """
    if created and instance.is_active:
        try:
            current_year = date.today().year
            summary = LeaveBalanceService.assign_annual_balances(
                year=current_year,
                user_ids=[instance.id],
                force_reset=False
            )

            if summary['balances_created'] > 0:
                logger.info(f"Assigned {summary['balances_created']} leave balances for new user {instance.username}")
            else:
                logger.warning(f"No leave balances assigned for new user {instance.username}")

        except Exception as e:
            logger.error(f"Error assigning leave balances for new user {instance.username}: {str(e)}")


# @receiver(post_save, sender=LeaveTypePolicy)
# Policy balance management is now handled in views.py for better control
# def handle_policy_changes(sender, instance, created, **kwargs):


# @receiver(pre_delete, sender=LeaveTypePolicy)
# Policy deletion is now handled in views.py for better control
# def handle_policy_deletion(sender, instance, **kwargs):


# @receiver(pre_save, sender=LeaveType)
# Leave type validation is now handled in views.py for proper API error handling
# def validate_leave_type_deactivation(sender, instance, **kwargs):


# @receiver(pre_delete, sender=LeaveType)
# Leave type deletion validation is now handled in views.py for proper API error handling
# def validate_leave_type_deletion(sender, instance, **kwargs):


def assign_policy_balances(policy):
    """
    Assign leave balances to users based on the policy
    """
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
                        # or if it had a different policy
                        if not balance.policy or balance.policy.id != policy.id:
                            balance.policy = policy
                            balance.opening_balance = policy.annual_quota
                            balance.save()
                            updated_count += 1
            
            logger.info(
                f"Policy {policy.name} activation: created {created_count} new balances, "
                f"updated {updated_count} existing balances"
            )
            
    except Exception as e:
        logger.error(f"Error assigning balances for policy {policy.name}: {str(e)}")
        raise


def remove_policy_balances(policy):
    """
    Remove leave balances for users who had this policy assigned
    """
    try:
        with transaction.atomic():
            # Find all balances that reference this policy
            balances_to_remove = LeaveBalance.objects.filter(policy=policy)
            
            # Log the removal
            count = balances_to_remove.count()
            if count > 0:
                logger.info(
                    f"Removing {count} leave balances for policy {policy.name} "
                    f"({policy.leave_type.name})"
                )
                
                # Remove the balances
                balances_to_remove.delete()
            
    except Exception as e:
        logger.error(f"Error removing balances for policy {policy.name}: {str(e)}")
        raise


@receiver(post_migrate)
def ensure_initial_leave_balances(sender, **kwargs):
    """
    Ensure all active users have leave balances after migrations
    """
    if sender.name == 'leave':
        try:
            current_year = date.today().year
            summary = LeaveBalanceService.assign_annual_balances(
                year=current_year,
                force_reset=False
            )

            if summary['total_users'] > 0:
                logger.info(f"Initial leave balance assignment completed: {summary['balances_created']} created, {summary['balances_updated']} updated")

        except Exception as e:
            logger.error(f"Error during initial leave balance assignment: {str(e)}")
