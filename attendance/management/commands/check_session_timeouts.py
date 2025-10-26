"""
Django management command to check for expired sessions and mark them as inactive.
This should be run as a cron job every 15 minutes for optimal session management.

Usage:
    python manage.py check_session_timeouts

Cron job example (run every 15 minutes):
    */15 * * * * cd /path/to/erms-backend && python manage.py check_session_timeouts >> /var/log/session_timeouts.log 2>&1
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from attendance.models import SessionLog


class Command(BaseCommand):
    help = 'Check for expired sessions and mark them as inactive for security and compliance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'[{timezone.now()}] Starting session timeout check...'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        try:
            if dry_run:
                # In dry run mode, just count what would be processed
                timeout_duration = timezone.timedelta(hours=1, minutes=15)
                cutoff_time = timezone.now() - timeout_duration
                
                expired_sessions = SessionLog.objects.filter(
                    is_session_active=True,
                    event_type='login',
                    last_activity__lt=cutoff_time
                )
                
                count = expired_sessions.count()
                self.stdout.write(
                    f'Would process {count} expired sessions'
                )
                
                if verbose:
                    for session in expired_sessions:
                        self.stdout.write(
                            f'  - User: {session.user.username}, '
                            f'Last activity: {session.last_activity}, '
                            f'Expired: {session.is_session_expired()}'
                        )
            else:
                # Actually process expired sessions
                expired_count = SessionLog.check_and_handle_expired_sessions()
                
                if expired_count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully marked {expired_count} expired sessions as inactive'
                        )
                    )
                else:
                    if verbose:
                        self.stdout.write('No expired sessions found')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'[{timezone.now()}] Session timeout check completed'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Error during session timeout check: {str(e)}'
                )
            )
            raise