from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.utils import timezone
from datetime import date
from accounts.models import User
from .models import LeaveTypePolicy, LeaveBalance
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


@receiver(post_save, sender=LeaveTypePolicy)
def assign_balances_for_policy_activation(sender, instance, created, **kwargs):
    """
    Assign leave balances when a leave policy is activated or updated
    """
    if instance.is_active and (created or kwargs.get('update_fields') is None or 'is_active' in kwargs.get('update_fields', [])):
        try:
            current_year = date.today().year
            # Get all active users who should have this policy
            users = User.objects.filter(is_active=True)

            user_ids = []
            for user in users:
                if instance.is_applicable_for_user(user):
                    user_ids.append(user.id)

            if user_ids:
                summary = LeaveBalanceService.assign_annual_balances(
                    year=current_year,
                    user_ids=user_ids,
                    force_reset=False
                )

                logger.info(f"Assigned/updated leave balances for {len(user_ids)} users for policy {instance.name}")

        except Exception as e:
            logger.error(f"Error assigning balances for policy {instance.name}: {str(e)}")


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
