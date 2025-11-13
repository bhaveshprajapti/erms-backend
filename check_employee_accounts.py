#!/usr/bin/env python3
"""
Check existing employee accounts for login testing
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

try:
    django.setup()
    
    from accounts.models import User
    
    print("🔍 Checking Employee Accounts")
    print("=" * 50)
    
    # Get all non-superuser accounts (employees)
    employees = User.objects.filter(is_superuser=False, deleted_at__isnull=True)
    
    print(f"📊 Found {employees.count()} employee accounts:")
    print()
    
    for emp in employees:
        print(f"👤 Employee: {emp.username}")
        print(f"   Name: {emp.first_name} {emp.last_name}")
        print(f"   Email: {emp.email}")
        print(f"   Active: {'✅' if emp.is_active else '❌'}")
        print(f"   Staff: {'✅' if emp.is_staff else '❌'}")
        print(f"   Superuser: {'✅' if emp.is_superuser else '❌'}")
        print(f"   Has Password: {'✅' if emp.password else '❌'}")
        print(f"   Joining Date: {emp.joining_date}")
        print("-" * 30)
    
    if employees.count() == 0:
        print("⚠️ No employee accounts found!")
        print("You may need to create an employee account first.")
        
        # Check if there are any users at all
        all_users = User.objects.filter(deleted_at__isnull=True)
        print(f"\n📋 All users in system: {all_users.count()}")
        
        for user in all_users:
            print(f"   - {user.username} ({'Admin' if user.is_superuser else 'Staff' if user.is_staff else 'Employee'})")
    
    print("\n💡 Login Tips:")
    print("   - Use the exact username (case-sensitive)")
    print("   - Make sure the account is active")
    print("   - Non-superuser accounts will redirect to employee dashboard")
    print("   - Superuser/staff accounts will redirect to admin dashboard")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
