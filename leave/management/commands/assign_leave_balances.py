from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import date
from leave.services import LeaveBalanceService
from leave.models import LeaveTypePolicy, User
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Assign leave balances to users based on active policies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            help='Year to assign balances for (default: current year)',
        )
        parser.add_argument(
            '--user-ids',
            nargs='+',
            type=int,
            help='Specific user IDs to assign balances for',
        )
        parser.add_argument(
            '--force-reset',
            action='store_true',
            help='Force reset existing balances',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--policy-id',
            type=int,
            help='Only assign balances for specific policy ID',
        )

    def handle(self, *args, **options):
        year = options.get('year') or date.today().year
        user_ids = options.get('user_ids')
        force_reset = options.get('force_reset', False)
        dry_run = options.get('dry_run', False)
        policy_id = options.get('policy_id')

        self.stdout.write(
            self.style.SUCCESS(f'Starting leave balance assignment for year {year}')
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No changes will be made')
            )

        try:
            # Get users to process
            if user_ids:
                users = User.objects.filter(id__in=user_ids, is_active=True)
                user_count = users.count()
                self.stdout.write(f'Processing {user_count} specific users')
            else:
                users = User.objects.filter(is_active=True)
                user_count = users.count()
                self.stdout.write(f'Processing {user_count} active users')

            if user_count == 0:
                self.stdout.write(self.style.WARNING('No active users found'))
                return

            # Get applicable policies
            if policy_id:
                policies = LeaveTypePolicy.objects.filter(
                    id=policy_id,
                    is_active=True
                )
                policy_count = policies.count()
                if policy_count == 0:
                    raise CommandError(f'No active policy found with ID {policy_id}')
            else:
                policies = LeaveTypePolicy.objects.filter(is_active=True)
                policy_count = policies.count()
                self.stdout.write(f'Found {policy_count} active policies')

            if policy_count == 0:
                self.stdout.write(self.style.WARNING('No active policies found'))
                return

            # Show what would be processed in dry run
            if dry_run:
                applicable_users = []
                for policy in policies:
                    for user in users:
                        if policy.is_applicable_for_user(user):
                            applicable_users.append((user, policy))

                self.stdout.write(f'Would assign balances for {len(applicable_users)} user-policy combinations')
                for user, policy in applicable_users[:10]:  # Show first 10
                    self.stdout.write(f'  {user.username} -> {policy.name} ({policy.leave_type.name})')
                if len(applicable_users) > 10:
                    self.stdout.write(f'  ... and {len(applicable_users) - 10} more')
                return

            # Process balance assignment
            summary = LeaveBalanceService.assign_annual_balances(
                year=year,
                user_ids=user_ids,
                force_reset=force_reset
            )

            # Display results
            self.stdout.write(
                self.style.SUCCESS(f'Balance assignment completed for {summary["total_users"]} users')
            )

            if summary['balances_created'] > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created {summary["balances_created"]} new balances')
                )

            if summary['balances_updated'] > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Updated {summary["balances_updated"]} existing balances')
                )

            if summary['balances_skipped'] > 0:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Skipped {summary["balances_skipped"]} balances')
                )

            if summary['errors']:
                self.stdout.write(
                    self.style.ERROR(f'✗ {len(summary["errors"])} errors occurred:')
                )
                for error in summary['errors']:
                    self.stdout.write(f'  - {error}')

        except Exception as e:
            raise CommandError(f'Error during balance assignment: {str(e)}')
