"""
Management command to fix leave applications with incorrect total_days
"""
from django.core.management.base import BaseCommand
from leave.models import LeaveApplication
from decimal import Decimal


class Command(BaseCommand):
    help = 'Fix leave applications with incorrect total_days (0 or incorrect values)'

    def handle(self, *args, **options):
        # Find all leave applications with total_days = 0
        applications = LeaveApplication.objects.filter(total_days=0)
        
        fixed_count = 0
        for app in applications:
            old_days = app.total_days
            
            self.stdout.write(
                f"Processing Leave #{app.id}: "
                f"Start={app.start_date}, End={app.end_date}, "
                f"is_half_day={app.is_half_day}, policy={app.policy}"
            )
            
            # Manually calculate to debug
            if app.is_half_day and app.start_date == app.end_date:
                calculated_days = Decimal('0.5')
            else:
                days = (app.end_date - app.start_date).days + 1
                if app.policy and not app.policy.include_weekends:
                    self.stdout.write(f"  Policy excludes weekends, calculating working days (Saturday is working day)...")
                    from datetime import timedelta
                    working_days = 0
                    current_date = app.start_date
                    while current_date <= app.end_date:
                        weekday = current_date.weekday()
                        self.stdout.write(f"    {current_date} is weekday {weekday} ({'working' if weekday != 6 else 'Sunday (off)'})")
                        if weekday != 6:  # Exclude only Sunday (6), Saturday (5) is working day
                            working_days += 1
                        current_date += timedelta(days=1)
                    days = working_days
                    self.stdout.write(f"  Working days: {working_days}")
                calculated_days = Decimal(str(days))
            
            self.stdout.write(f"  Calculated days: {calculated_days}")
            
            # Call clean() to recalculate total_days
            app.clean()
            app.save()
            
            self.stdout.write(
                f"  After clean(): {app.total_days} days"
            )
            
            self.stdout.write(
                f"Fixed Leave #{app.id}: {app.start_date} to {app.end_date} - "
                f"Changed from {old_days} to {app.total_days} days\n"
            )
            fixed_count += 1
        
        if fixed_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully fixed {fixed_count} leave applications')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('No leave applications need fixing')
            )
