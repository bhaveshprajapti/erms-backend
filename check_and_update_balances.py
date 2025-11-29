"""
Check current balance state and update them
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from leave.models import LeaveBalance, LeaveTypePolicy
from datetime import date

print("="*60)
print("Checking Current Leave Balances")
print("="*60)

# Check current state
balances = LeaveBalance.objects.filter(year=2025).select_related('policy', 'user', 'leave_type')
print(f"\nTotal balances for 2025: {balances.count()}")

# Show sample of current state
print("\nCurrent state (first 10):")
for b in balances[:10]:
    max_month = b.policy.max_per_month if b.policy else None
    print(f"  {b.user.username} - {b.leave_type.name}: max_per_month={max_month}, policy={b.policy.name if b.policy else 'None'}")

# Check policies
print("\n" + "="*60)
print("Current Active Policies")
print("="*60)
policies = LeaveTypePolicy.objects.filter(is_active=True)
for p in policies:
    print(f"\nPolicy: {p.name} ({p.leave_type.name})")
    print(f"  max_per_month: {p.max_per_month}")
    print(f"  annual_quota: {p.annual_quota}")
    print(f"  effective_from: {p.effective_from}")
    print(f"  Balances using this policy: {LeaveBalance.objects.filter(policy=p, year=2025).count()}")

# Now update balances
print("\n" + "="*60)
print("Updating Balances")
print("="*60)

from django.db import transaction

updated_count = 0
skipped_count = 0

with transaction.atomic():
    for policy in policies:
        # Check if policy is currently effective
        current_date = date.today()
        if policy.effective_from > current_date:
            print(f"\nSkipping {policy.name} - not yet effective")
            continue
        
        if policy.effective_to and policy.effective_to < current_date:
            print(f"\nSkipping {policy.name} - already expired")
            continue
        
        print(f"\nProcessing policy: {policy.name}")
        
        # Find balances for this leave type
        balances_to_update = LeaveBalance.objects.filter(
            leave_type=policy.leave_type,
            year=2025
        ).select_related('user')
        
        for balance in balances_to_update:
            # Check if policy is applicable to this user
            if policy.is_applicable_for_user(balance.user):
                old_policy = balance.policy.name if balance.policy else "None"
                balance.policy = policy
                balance.save(update_fields=['policy', 'updated_at'])
                print(f"  Updated {balance.user.username}: {old_policy} -> {policy.name}")
                updated_count += 1
            else:
                skipped_count += 1

print("\n" + "="*60)
print("Summary")
print("="*60)
print(f"Updated: {updated_count} balances")
print(f"Skipped: {skipped_count} balances")

# Show updated state
print("\n" + "="*60)
print("Updated State (first 10)")
print("="*60)
balances = LeaveBalance.objects.filter(year=2025).select_related('policy', 'user', 'leave_type')
for b in balances[:10]:
    max_month = b.policy.max_per_month if b.policy else None
    print(f"  {b.user.username} - {b.leave_type.name}: max_per_month={max_month}, policy={b.policy.name if b.policy else 'None'}")

print("\n✅ Done! Balances have been updated.")
