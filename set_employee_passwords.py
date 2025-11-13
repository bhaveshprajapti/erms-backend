#!/usr/bin/env python3
"""
Set passwords for existing employee accounts
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
    
    print("🔧 Setting Passwords for Employee Accounts")
    print("=" * 50)
    
    # Get employee accounts without passwords
    employees = User.objects.filter(is_superuser=False, deleted_at__isnull=True)
    
    # Set default password for testing
    default_password = "Employee@123"
    
    for emp in employees:
        if not emp.password or not emp.check_password(default_password):
            emp.set_password(default_password)
            emp.save()
            print(f"✅ Password set for: {emp.username}")
            print(f"   Username: {emp.username}")
            print(f"   Password: {default_password}")
            print(f"   Name: {emp.first_name} {emp.last_name}")
            print(f"   Email: {emp.email}")
            print("-" * 30)
        else:
            print(f"⚠️ Password already set for: {emp.username}")
    
    print(f"\n🎉 Password setup complete!")
    print(f"📋 You can now login with any of these employee accounts:")
    print(f"   Username: DW_bhavesh")
    print(f"   Password: {default_password}")
    print()
    print(f"   Username: dsfsdfdsfsdf") 
    print(f"   Password: {default_password}")
    print()
    print(f"   Username: test_employee_folder")
    print(f"   Password: {default_password}")
    print()
    print(f"   Username: test1")
    print(f"   Password: {default_password}")
    print()
    print("🔄 After login, employees will be redirected to /employee-dashboard")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
