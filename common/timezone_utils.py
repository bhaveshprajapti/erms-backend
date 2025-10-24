"""
Comprehensive Timezone Utilities for IST Business Logic with UTC Storage

This module provides utilities for the backend to:
1. Store all timestamps in UTC (database standard)
2. Use IST for all business logic (dates, validations)
3. Convert between UTC and IST consistently
4. Handle cross-midnight scenarios correctly
"""

from datetime import datetime, date, time, timedelta
from django.utils import timezone
from zoneinfo import ZoneInfo

# IST timezone constant
IST_TIMEZONE = ZoneInfo("Asia/Kolkata")

def get_ist_time(utc_time=None):
    """
    Convert UTC time to IST (Indian Standard Time)
    
    Args:
        utc_time: UTC datetime object. If None, uses current UTC time.
    
    Returns:
        IST datetime object
    """
    if utc_time is None:
        utc_time = timezone.now()
    
    # Convert to IST (UTC+5:30)
    return utc_time.astimezone(IST_TIMEZONE)

def get_ist_date(utc_time=None):
    """
    Get IST date from UTC time
    
    Args:
        utc_time: UTC datetime object. If None, uses current UTC time.
    
    Returns:
        IST date object
    """
    ist_time = get_ist_time(utc_time)
    return ist_time.date()

def get_current_ist_date():
    """
    Get current date in IST
    
    Returns:
        Current IST date object
    """
    return get_ist_date()

def get_utc_range_for_ist_date(ist_date):
    """
    Get UTC datetime range for a specific IST date
    
    Args:
        ist_date: date object or string (YYYY-MM-DD) in IST
    
    Returns:
        tuple: (start_utc, end_utc) datetime objects
    """
    if isinstance(ist_date, str):
        ist_date = datetime.strptime(ist_date, '%Y-%m-%d').date()
    
    # Start of IST date (00:00:00 IST)
    ist_start = datetime.combine(ist_date, time.min, tzinfo=IST_TIMEZONE)
    utc_start = ist_start.astimezone(timezone.utc)
    
    # End of IST date (23:59:59.999999 IST)
    ist_end = datetime.combine(ist_date, time.max, tzinfo=IST_TIMEZONE)
    utc_end = ist_end.astimezone(timezone.utc)
    
    return utc_start, utc_end

def convert_ist_datetime_to_utc(ist_datetime):
    """
    Convert IST datetime to UTC
    
    Args:
        ist_datetime: datetime object in IST (naive or aware)
    
    Returns:
        UTC datetime object
    """
    if ist_datetime.tzinfo is None:
        # Assume naive datetime is in IST
        ist_datetime = ist_datetime.replace(tzinfo=IST_TIMEZONE)
    
    return ist_datetime.astimezone(timezone.utc)

def convert_utc_datetime_to_ist(utc_datetime):
    """
    Convert UTC datetime to IST
    
    Args:
        utc_datetime: datetime object in UTC
    
    Returns:
        IST datetime object
    """
    if utc_datetime.tzinfo is None:
        utc_datetime = timezone.make_aware(utc_datetime, timezone.utc)
    
    return utc_datetime.astimezone(IST_TIMEZONE)

def parse_ist_date_string(date_string):
    """
    Parse IST date string to date object
    
    Args:
        date_string: Date string in format YYYY-MM-DD (assumed IST)
    
    Returns:
        date object
    """
    return datetime.strptime(date_string, '%Y-%m-%d').date()

def format_ist_datetime(ist_datetime, include_timezone=True):
    """
    Format IST datetime for display
    
    Args:
        ist_datetime: datetime object in IST
        include_timezone: Whether to include timezone info
    
    Returns:
        Formatted string
    """
    if include_timezone:
        return ist_datetime.strftime('%Y-%m-%d %H:%M:%S %Z')
    else:
        return ist_datetime.strftime('%Y-%m-%d %H:%M:%S')

def is_same_ist_date(utc_datetime1, utc_datetime2):
    """
    Check if two UTC datetimes fall on the same IST date
    
    Args:
        utc_datetime1: First UTC datetime
        utc_datetime2: Second UTC datetime
    
    Returns:
        bool: True if same IST date
    """
    ist_date1 = get_ist_date(utc_datetime1)
    ist_date2 = get_ist_date(utc_datetime2)
    return ist_date1 == ist_date2

def get_ist_business_date(utc_datetime=None, early_cutoff_hour=6):
    """
    Get IST business date (handles cross-midnight scenarios)
    
    If it's before early_cutoff_hour AM IST, consider it as previous business day.
    This is useful for night shift workers.
    
    Args:
        utc_datetime: UTC datetime. If None, uses current time.
        early_cutoff_hour: Hour before which to consider as previous day (default: 6 AM)
    
    Returns:
        IST business date
    """
    ist_datetime = get_ist_time(utc_datetime)
    
    # If before cutoff hour IST, consider it as previous day for business purposes
    if ist_datetime.hour < early_cutoff_hour:
        business_date = ist_datetime.date() - timedelta(days=1)
    else:
        business_date = ist_datetime.date()
    
    return business_date

def get_week_start_end_ist(ist_date=None):
    """
    Get week start and end dates in IST (Monday to Sunday)
    
    Args:
        ist_date: IST date. If None, uses current IST date.
    
    Returns:
        tuple: (week_start_date, week_end_date) in IST
    """
    if ist_date is None:
        ist_date = get_current_ist_date()
    
    # Monday is 0, Sunday is 6
    days_since_monday = ist_date.weekday()
    week_start = ist_date - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    
    return week_start, week_end

def get_month_start_end_ist(year=None, month=None):
    """
    Get month start and end dates in IST
    
    Args:
        year: Year. If None, uses current IST year.
        month: Month. If None, uses current IST month.
    
    Returns:
        tuple: (month_start_date, month_end_date) in IST
    """
    if year is None or month is None:
        current_ist = get_current_ist_date()
        year = year or current_ist.year
        month = month or current_ist.month
    
    month_start = date(year, month, 1)
    
    # Get last day of month
    if month == 12:
        next_month_start = date(year + 1, 1, 1)
    else:
        next_month_start = date(year, month + 1, 1)
    
    month_end = next_month_start - timedelta(days=1)
    
    return month_start, month_end

def validate_ist_date_range(start_date, end_date):
    """
    Validate IST date range
    
    Args:
        start_date: Start date (string or date object)
        end_date: End date (string or date object)
    
    Returns:
        tuple: (is_valid, error_message, parsed_start_date, parsed_end_date)
    """
    try:
        if isinstance(start_date, str):
            start_date = parse_ist_date_string(start_date)
        if isinstance(end_date, str):
            end_date = parse_ist_date_string(end_date)
        
        if start_date > end_date:
            return False, "Start date cannot be after end date", None, None
        
        # Check if dates are too far in the future (business rule)
        current_date = get_current_ist_date()
        max_future_date = current_date + timedelta(days=365)  # 1 year ahead
        
        if start_date > max_future_date:
            return False, "Start date cannot be more than 1 year in the future", None, None
        
        return True, "", start_date, end_date
        
    except ValueError as e:
        return False, f"Invalid date format: {str(e)}", None, None

def get_working_days_between_ist_dates(start_date, end_date, exclude_weekends=True):
    """
    Calculate working days between two IST dates
    
    Args:
        start_date: Start date (IST)
        end_date: End date (IST)
        exclude_weekends: Whether to exclude weekends
    
    Returns:
        int: Number of working days
    """
    if isinstance(start_date, str):
        start_date = parse_ist_date_string(start_date)
    if isinstance(end_date, str):
        end_date = parse_ist_date_string(end_date)
    
    total_days = (end_date - start_date).days + 1
    
    if not exclude_weekends:
        return total_days
    
    # Count weekdays only
    working_days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Monday is 0, Sunday is 6
        if current_date.weekday() != 6:  # Monday to Saturday (exclude only Sunday)
            working_days += 1
        current_date += timedelta(days=1)
    
    return working_days

# Backward compatibility aliases
def today_ist():
    """Get current IST date - backward compatibility"""
    return get_current_ist_date()

def now_ist():
    """Get current IST datetime - backward compatibility"""
    return get_ist_time()