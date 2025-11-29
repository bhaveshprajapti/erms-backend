"""
Management command to apply leave policies based on their effective_from date
This should be run daily (via cron/scheduler) to automatically activate policies
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date
from leave.models import LeaveTypePolicy, LeaveBalance
from accounts.models import User
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Apply leave policies that have become effective today'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-date',
            type=str,
            default=None,
            help='Check for policies effective on this date (YYYY-MM-DD). Default: today'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be applied without making changes'
        )

    def handle(self, *args, **options):
        check_date_str = options['check_date']
        dry_run = options['dry_run']

        if check_date_str:
            try:
                check_date = date.fromisoformat(check_date_str)
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Invalid date format: {check_date_str}"))
                return
        else:
            check_date = date.today()

        self.stdout.write(f"Checking for policies effective on {check_date}...")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Find policies that become effective today
        policies_to_apply = LeaveTypePolicy.objects.filter(
            is_active=True,
            effective_from=check_date
        ).select_related('leave_type')

        if not policies_to_apply.exists():
            self.stdout.write(self.style.SUCCESS(f"No policies become effective on {check_date}"))
            return

        self.stdout.write(f"\nFound {policies_to_apply.count()} policies to apply:")
        for policy in policies_to_apply:
            self.stdout.write(f"  - {policy.name} ({policy.leave_type.name})")

        total_created = 0
        total_updated = 0
        total_errors = 0

        with transaction.atomic():
            for policy in policies_to_apply:
                try:
                    summary = self._apply_policy_to_users(policy, check_date.year, dry_run)
                    total_created += summary['created']
                    total_updated += summary['updated']
                    
                    self.stdout.write(
                        f"\n  {policy.name}:"
                        f"\n    Created: {summary['created']} balances"
                        f"\n    Updated: {summary['updated']} balances"
                        f"\n    Skipped: {summary['skipped']} users"
                    )
                    
                except Exception as e:
                    total_errors += 1
                    self.stdout.write(
                        self.style.ERROR(f"\n  Error applying {policy.name}: {str(e)}")
                    )
                    logger.error(f"Error applying policy {policy.name}: {str(e)}")

            if dry_run:
                # Rollback in dry run mode
                transaction.set_rollback(True)

        # Print summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("Summary:"))
        self.stdout.write(f"  Policies processed: {policies_to_apply.count()}")
        self.stdout.write(self.style.SUCCESS(f"  Balances created: {total_created}"))
        self.stdout.write(self.style.SUCCESS(f"  Balances updated: {total_updated}"))
        if total_errors > 0:
            self.stdout.write(self.style.ERROR(f"  Errors: {total_errors}"))

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nDRY RUN completed - no changes were made. "
                    "Run without --dry-run to apply changes."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully applied {policies_to_apply.count()} policies!"
                )
            )

    def _apply_policy_to_users(self, policy, year, dry_run=False):
        """Apply a policy to all applicable users"""
        summary = {'created': 0, 'updated': 0, 'skipped': 0}

        # Get all active users
        users = User.objects.filter(is_active=True)

        for user in users:
            # Check if policy is applicable to this user
            if not policy.is_applicable_for_user(user):
                summary['skipped'] += 1
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
                summary['created'] += 1
                logger.info(
                    f"Created balance for {user.username} - {policy.leave_type.name} "
                    f"with policy {policy.name}"
                )
            else:
                # Update existing balance to use new policy
                # Only update policy reference, keep balances intact
                if not dry_run:
                    balance.policy = policy
                    balance.save(update_fields=['policy', 'updated_at'])
                
                summary['updated'] += 1
                logger.info(
                    f"Updated balance for {user.username} - {policy.leave_type.name} "
                    f"to use policy {policy.name}"
                )

        return summary
