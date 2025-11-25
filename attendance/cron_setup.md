# Daily Attendance Status Update - Cron Job Setup

## Overview
This cron job runs daily to update attendance status (Present/Absent/Half Day) for all users after the day is complete.

## Setup Instructions

### 1. Add to crontab
Run `crontab -e` and add the following line:

```bash
# Update daily attendance status at 11:59 PM every day
59 23 * * * cd /path/to/erms-backend && python manage.py update_daily_attendance
```

### 2. Alternative: Using Django-Crontab (Recommended)

Install django-crontab:
```bash
pip install django-crontab
```

Add to INSTALLED_APPS in settings.py:
```python
INSTALLED_APPS = [
    # ... other apps
    'django_crontab',
]
```

Add to settings.py:
```python
CRONJOBS = [
    ('59 23 * * *', 'attendance.management.commands.update_daily_attendance.Command'),
]
```

Then run:
```bash
python manage.py crontab add
python manage.py crontab show  # to verify
```

### 3. Manual Execution
You can also run the command manually:

```bash
# Update for yesterday (default)
python manage.py update_daily_attendance

# Update for specific date
python manage.py update_daily_attendance --date 2024-01-15
```

## What it does
- Processes all active users
- Calculates attendance status based on:
  - Check-in sessions
  - Total working hours vs shift duration
  - Leave status
- Updates attendance records with final status
- Runs at 11:59 PM to ensure the day is complete

## Status Calculation Logic
- **On Leave**: User has approved leave and no attendance recorded
- **Present**: Worked >= 75% of shift duration
- **Present (Despite Leave)**: Had approved leave but worked >= 75% of shift
- **Half Day**: Worked >= 50% but < 75% of shift duration  
- **Half Day (Despite Leave)**: Had approved leave but worked 50-75% of shift
- **Absent**: No check-in or worked < 50% of shift duration

## Special Cases
- If user has approved leave but still comes to office and works, status reflects actual work done
- For current day, shows "Active" if checked in, "Present" if checked out
- End-of-day calculation overrides real-time status with final calculated status