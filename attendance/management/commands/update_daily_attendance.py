from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from attendance.models import Attendance
from accounts.models import User
from common.models import StatusChoice


class Command(BaseCommand):
    help = 'Update daily attendance status for all users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to process (YYYY-MM-DD format). Defaults to yesterday.',
        )

    def handle(self, *args, **options):
        # Get the date to process
        if options['date']:
            try:
                process_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid date format. Use YYYY-MM-DD.')
                )
                return
        else:
            # Default to yesterday
            process_date = (timezone.now() - timedelta(days=1)).date()

        self.stdout.write(f'Processing attendance for date: {process_date}')

        # Get all users
        users = User.objects.filter(is_active=True)
        updated_count = 0
        
        for user in users:
            try:
                # Get or create attendance record for the date
                attendance, created = Attendance.objects.get_or_create(
                    user=user,
                    date=process_date,
                    defaults={'sessions': []}
                )
                
                sessions = attendance.sessions or []
                
                # Calculate attendance status
                status = self._calculate_attendance_status(user, process_date, sessions, attendance.total_hours)
                
                # Update attendance record with calculated status
                if not hasattr(attendance, 'status') or attendance.status != status:
                    # You might want to add a status field to the Attendance model
                    # For now, we'll add it to the sessions data
                    if 'daily_status' not in (attendance.sessions or {}):
                        if isinstance(attendance.sessions, list):
                            attendance.sessions = {'sessions': attendance.sessions, 'daily_status': status}
                        else:
                            attendance.sessions['daily_status'] = status
                        attendance.save()
                        updated_count += 1
                        
                        self.stdout.write(f'Updated {user.username}: {status}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing user {user.username}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} attendance records for {process_date}')
        )

    def _get_user_shifts(self, user):
        """Get user's active shifts"""
        return user.shifts.filter(is_active=True)

    def _check_leave_status(self, user, date):
        """Check if user is on approved leave for the given date"""
        from attendance.models import LeaveRequest
        
        try:
            # Try to get approved status
            approved_status = None
            try:
                approved_status = StatusChoice.objects.get(category='leave_status', name__iexact='Approved')
            except StatusChoice.DoesNotExist:
                pass
            
            # Filter for approved leaves
            leave_requests = LeaveRequest.objects.filter(
                user=user,
                start_date__lte=date,
                end_date__gte=date
            )
            
            # Filter for approved leaves only
            if approved_status:
                leave_requests = leave_requests.filter(status=approved_status)
            else:
                # Fallback: assume status = 2 means approved
                leave_requests = leave_requests.filter(status=2)
            
            return leave_requests.exists()
        except:
            return False

    def _calculate_attendance_status(self, user, date, sessions, total_hours):
        """Calculate attendance status (Present/Absent/Half Day) based on sessions and hours"""
        has_approved_leave = self._check_leave_status(user, date)
        
        # If no sessions recorded
        if not sessions:
            if has_approved_leave:
                return 'On Leave'
            return 'Absent'
        
        # If user has sessions, prioritize actual attendance over leave status
        # This handles cases where employees come to office even after approved leave
        if sessions:
            # Calculate total working hours
            total_seconds = 0
            if total_hours:
                time_parts = str(total_hours).split(':')
                hours = int(time_parts[0]) if len(time_parts) > 0 else 0
                minutes = int(time_parts[1]) if len(time_parts) > 1 else 0
                seconds = float(time_parts[2]) if len(time_parts) > 2 else 0
                total_seconds = hours * 3600 + minutes * 60 + seconds
            
            # Get user shifts to determine minimum working hours
            shifts = self._get_user_shifts(user)
            min_hours = 8 * 3600  # Default 8 hours in seconds
            
            if shifts.exists():
                shift = shifts.first()
                start_time = shift.start_time
                end_time = shift.end_time
                
                # Calculate shift duration
                start_seconds = start_time.hour * 3600 + start_time.minute * 60
                end_seconds = end_time.hour * 3600 + end_time.minute * 60
                
                if end_seconds > start_seconds:
                    min_hours = end_seconds - start_seconds
                else:
                    # Overnight shift
                    min_hours = (24 * 3600 - start_seconds) + end_seconds
            
            # Determine status based on working hours
            # If user had approved leave but still came to office, mark based on actual work
            if total_seconds >= min_hours * 0.75:  # 75% of shift duration
                if has_approved_leave:
                    return 'Present (Despite Leave)'  # Special status for leave override
                return 'Present'
            elif total_seconds >= min_hours * 0.5:  # 50% of shift duration
                if has_approved_leave:
                    return 'Half Day (Despite Leave)'
                return 'Half Day'
            elif total_seconds > 0:  # Has some working time
                if has_approved_leave:
                    return 'Half Day (Despite Leave)'
                return 'Half Day'
            else:
                # Has sessions but no working time (check-in only)
                if has_approved_leave:
                    return 'On Leave'  # Respect leave if no actual work done
                return 'Absent'
        
        # Fallback
        if has_approved_leave:
            return 'On Leave'
        return 'Absent'