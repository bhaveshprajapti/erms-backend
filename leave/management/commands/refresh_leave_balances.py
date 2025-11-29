"""
Management command to refresh leave balances with current policies
This ensures all user balances reference the correct, up-to-date policies
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date
from leave.models import LeaveBalance, LeaveTypePolicy
from accounts.models import User


class Command(BaseCommand):
    help = 'Refresh leave balances to use current active policies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            default=None,
            help='Year to refresh balances for (default: current year)'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            default=None,
            help='Specific user ID to refresh (default: all users)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )

    def handle(self, *args, **options):
        year = options['year'] or date.today().year
        user_id = options['user_id']
        dry_run = options['dry_run']

        self.stdout.write(f"Refreshing leave balances for year {year}...")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Get balances to process
        balances_query = LeaveBalance.objects.filter(year=year).select_related(
            'user', 'leave_type', 'policy'
        )
        
        if user_id:
            balances_query = balances_query.filter(user_id=user_id)

        balances = list(balances_query)
        
        if not balances:
            self.stdout.write(self.style.WARNING(f"No balances found for year {year}"))
            return

        updated_count = 0
        skipped_count = 0
        error_count = 0

        with transaction.atomic():
            for balance in balances:
                try:
                    # Find the applicable policy for this user and leave type
                    applicable_policy = self._get_applicable_policy(
                        balance.user, 
                        balance.leave_type, 
                        year
                    )

                    if not applicable_policy:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  No applicable policy found for {balance.user.username} - "
                                f"{balance.leave_type.name}"
                            )
                        )
                        skipped_count += 1
                        continue

                    # Check if policy needs updating
                    if balance.policy != applicable_policy:
                        old_policy_name = balance.policy.name if balance.policy else "None"
                        
                        self.stdout.write(
                            f"  Updating {balance.user.username} - {balance.leave_type.name}: "
                            f"{old_policy_name} -> {applicable_policy.name}"
                        )

                        if not dry_run:
                            balance.policy = applicable_policy
                            balance.save(update_fields=['policy', 'updated_at'])
                        
                        updated_count += 1
                    else:
                        skipped_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  Error processing {balance.user.username} - "
                            f"{balance.leave_type.name}: {str(e)}"
                        )
                    )
                    error_count += 1

            if dry_run:
                # Rollback transaction in dry run mode
                transaction.set_rollback(True)

        # Print summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"Summary:"))
        self.stdout.write(f"  Total balances processed: {len(balances)}")
        self.stdout.write(self.style.SUCCESS(f"  Updated: {updated_count}"))
        self.stdout.write(f"  Skipped (already correct): {skipped_count}")
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"  Errors: {error_count}"))
        
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
                    f"\nSuccessfully refreshed {updated_count} leave balances!"
                )
            )

    def _get_applicable_policy(self, user, leave_type, year):
        """Find the most applicable policy for a user and leave type"""
        from django.db.models import Q
        
        policies = LeaveTypePolicy.objects.filter(
            leave_type=leave_type,
            is_active=True,
            effective_from__lte=date(year, 12, 31)
        ).filter(
            Q(effective_to__isnull=True) | 
            Q(effective_to__gte=date(year, 1, 1))
        )

        for policy in policies:
            if policy.is_applicable_for_user(user):
                return policy

        return None
