"""
Utility functions for clients app
"""
from django.utils import timezone
import random


def generate_unique_quotation_number():
    """
    Generate a unique quotation number in format: QT-DW-DDMMYYYY-XXXXXX
    
    Format breakdown:
    - QT: Quotation prefix
    - DW: DigiWave company identifier
    - DDMMYYYY: Current date in IST
    - XXXXXX: Unique 6-digit combination (timestamp + random)
    
    Example: QT-DW-18102024-123456
    """
    # Get current IST time
    now = timezone.now()
    # Convert to IST (UTC+5:30)
    ist_time = now + timezone.timedelta(hours=5, minutes=30)
    
    # Format date as DDMMYYYY
    day = ist_time.day
    month = ist_time.month
    year = ist_time.year
    date_str = f"{day:02d}{month:02d}{year}"
    
    # Generate unique number combination
    # Use timestamp (last 4 digits) + random 2 digits for uniqueness
    timestamp_part = str(int(ist_time.timestamp()))[-4:]
    random_part = f"{random.randint(10, 99)}"
    unique_num = f"{timestamp_part}{random_part}"
    
    # Format: QT-DW-DDMMYYYY-XXXXXX
    quotation_no = f"QT-DW-{date_str}-{unique_num}"
    
    return quotation_no


def ensure_unique_quotation_number():
    """
    Generate a quotation number and ensure it's unique in the database
    """
    from .models import Quotation
    
    quotation_no = generate_unique_quotation_number()
    
    # Ensure uniqueness by checking if it already exists
    while Quotation.objects.filter(quotation_no=quotation_no).exists():
        quotation_no = generate_unique_quotation_number()
    
    return quotation_no