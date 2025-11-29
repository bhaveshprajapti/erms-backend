"""
Test script to verify leave policy max_per_month fix
Run with: python manage.py shell < test_leave_policy_fix.py
"""
import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from leave.models import LeaveType, LeaveTypePolicy, LeaveBalance
from accounts.models import User
from datetime import date
from decimal import Decimal

# Use timestamp to ensure unique names
timestamp = int(time.time())

print("="*60)
print("Testing Leave Policy Max Per Month Fix")
print("="*60)

# Test 1: Create policy with NULL max_per_month
print("\n1. Testing NULL (no limit) for max_per_month...")
try:
    leave_type = LeaveType.objects.first()
    if not leave_type:
        print("   ❌ No leave type found. Please create one first.")
    else:
        policy = LeaveTypePolicy.objects.create(
            name=f"Test Policy - No Limit {timestamp}",
            leave_type=leave_type,
            annual_quota=20,
            max_per_month=None,  # No limit
            is_active=False  # Don't activate to avoid affecting real data
        )
        
        if policy.max_per_month is None:
            print("   ✅ Policy created with max_per_month=NULL (no limit)")
        else:
            print(f"   ❌ Expected NULL but got: {policy.max_per_month}")
        
        policy.delete()
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# Test 2: Create policy with specific limit
print("\n2. Testing specific limit (5 days) for max_per_month...")
try:
    policy = LeaveTypePolicy.objects.create(
        name=f"Test Policy - 5 Days {timestamp}",
        leave_type=leave_type,
        annual_quota=20,
        max_per_month=5,
        is_active=False
    )
    
    if policy.max_per_month == 5:
        print("   ✅ Policy created with max_per_month=5")
    else:
        print(f"   ❌ Expected 5 but got: {policy.max_per_month}")
    
    policy.delete()
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# Test 3: Update policy from specific to NULL
print("\n3. Testing update from specific limit to no limit...")
try:
    policy = LeaveTypePolicy.objects.create(
        name=f"Test Policy - Update {timestamp}",
        leave_type=leave_type,
        annual_quota=20,
        max_per_month=5,
        is_active=False
    )
    
    print(f"   Initial: max_per_month={policy.max_per_month}")
    
    policy.max_per_month = None
    policy.save()
    policy.refresh_from_db()
    
    if policy.max_per_month is None:
        print("   ✅ Policy updated to max_per_month=NULL (no limit)")
    else:
        print(f"   ❌ Expected NULL but got: {policy.max_per_month}")
    
    policy.delete()
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# Test 4: Verify balance validation with NULL
print("\n4. Testing leave balance validation with NULL limit...")
try:
    user = User.objects.filter(is_active=True).first()
    if not user:
        print("   ⚠️  No active user found. Skipping balance test.")
    else:
        policy = LeaveTypePolicy.objects.create(
            name=f"Test Policy - Validation {timestamp}",
            leave_type=leave_type,
            annual_quota=20,
            max_per_month=None,  # No limit
            is_active=False
        )
        
        # Use a future year to avoid conflicts
        test_year = date.today().year + 1
        
        balance = LeaveBalance.objects.create(
            user=user,
            leave_type=leave_type,
            policy=policy,
            year=test_year,
            opening_balance=20
        )
        
        # Try to apply for 15 days (should pass with no limit)
        can_apply, message = balance.can_apply_for_days(
            Decimal('15'), 
            date.today()
        )
        
        if can_apply:
            print("   ✅ Validation passed: Can apply for 15 days with no monthly limit")
        else:
            print(f"   ❌ Validation failed: {message}")
        
        balance.delete()
        policy.delete()
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

# Test 5: Verify balance validation with specific limit
print("\n5. Testing leave balance validation with specific limit...")
try:
    if user:
        policy = LeaveTypePolicy.objects.create(
            name=f"Test Policy - Validation 2 {timestamp}",
            leave_type=leave_type,
            annual_quota=20,
            max_per_month=5,  # 5 days limit
            is_active=False
        )
        
        # Use a future year to avoid conflicts
        test_year = date.today().year + 2
        
        balance = LeaveBalance.objects.create(
            user=user,
            leave_type=leave_type,
            policy=policy,
            year=test_year,
            opening_balance=20
        )
        
        # Try to apply for 3 days (should pass)
        can_apply, message = balance.can_apply_for_days(
            Decimal('3'), 
            date.today()
        )
        
        if can_apply:
            print("   ✅ Validation passed: Can apply for 3 days with 5-day limit")
        else:
            print(f"   ❌ Validation failed: {message}")
        
        # Try to apply for 10 days (should fail)
        can_apply, message = balance.can_apply_for_days(
            Decimal('10'), 
            date.today()
        )
        
        if not can_apply and "Monthly limit exceeded" in message:
            print("   ✅ Validation correctly rejected: Cannot apply for 10 days with 5-day limit")
        else:
            print(f"   ❌ Expected rejection but got: can_apply={can_apply}, message={message}")
        
        balance.delete()
        policy.delete()
except Exception as e:
    print(f"   ❌ Error: {str(e)}")

print("\n" + "="*60)
print("Test Summary")
print("="*60)
print("All tests completed. Check results above.")
print("✅ = Pass, ❌ = Fail, ⚠️  = Skipped")
print("="*60)
