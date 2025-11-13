"""
Django management command to clean up expired JWT tokens and blacklisted tokens.
This should be run as a cron job daily for optimal performance.

Usage:
    python manage.py cleanup_expired_tokens

Cron job example (run daily at 2 AM):
    0 2 * * * cd /path/to/erms-backend && python manage.py cleanup_expired_tokens >> /var/log/token_cleanup.log 2>&1
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Clean up expired JWT tokens and blacklisted tokens for better performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it',
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
                f'[{timezone.now()}] Starting token cleanup...'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        try:
            # Clean up blacklisted tokens older than 30 days
            from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
            
            # Calculate cutoff date (30 days ago)
            cutoff_date = timezone.now() - timedelta(days=30)
            
            if dry_run:
                # Count what would be deleted
                old_blacklisted = BlacklistedToken.objects.filter(
                    token__created_at__lt=cutoff_date
                ).count()
                
                old_outstanding = OutstandingToken.objects.filter(
                    created_at__lt=cutoff_date,
                    blacklistedtoken__isnull=False
                ).count()
                
                self.stdout.write(
                    f'Would delete {old_blacklisted} blacklisted tokens and {old_outstanding} outstanding tokens'
                )
                
            else:
                # Actually delete old tokens
                deleted_blacklisted, _ = BlacklistedToken.objects.filter(
                    token__created_at__lt=cutoff_date
                ).delete()
                
                deleted_outstanding, _ = OutstandingToken.objects.filter(
                    created_at__lt=cutoff_date,
                    blacklistedtoken__isnull=False
                ).delete()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Deleted {deleted_blacklisted} blacklisted tokens and {deleted_outstanding} outstanding tokens'
                    )
                )
            
            # Clean up very old outstanding tokens (older than 60 days)
            very_old_cutoff = timezone.now() - timedelta(days=60)
            
            if dry_run:
                very_old_count = OutstandingToken.objects.filter(
                    created_at__lt=very_old_cutoff
                ).count()
                
                self.stdout.write(
                    f'Would delete {very_old_count} very old outstanding tokens'
                )
            else:
                deleted_very_old, _ = OutstandingToken.objects.filter(
                    created_at__lt=very_old_cutoff
                ).delete()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Deleted {deleted_very_old} very old outstanding tokens'
                    )
                )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'[{timezone.now()}] Token cleanup completed successfully'
                )
            )
            
        except ImportError:
            self.stdout.write(
                self.style.WARNING(
                    'Token blacklist not available - skipping token cleanup'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Error during token cleanup: {str(e)}'
                )
            )
            raise