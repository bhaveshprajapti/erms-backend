#!/usr/bin/env python3
"""
Check available roles and employee types
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

django.setup()

from accounts.models import Role
from common.models import EmployeeType

print("🔍 Checking Available Roles and Employee Types")
print("=" * 50)

print("📋 Available Roles:")
roles = Role.objects.all()
if roles:
    for role in roles:
        print(f"   ID: {role.id} - {role.display_name} ({role.name})")
else:
    print("   ❌ No roles found!")

print("\n📋 Available Employee Types:")
emp_types = EmployeeType.objects.all()
if emp_types:
    for emp_type in emp_types:
        print(f"   ID: {emp_type.id} - {emp_type.name}")
else:
    print("   ❌ No employee types found!")

# If no roles exist, create a default one
if not roles:
    print("\n🔧 Creating default role...")
    default_role = Role.objects.create(
        name="employee",
        display_name="Employee",
        description="Default employee role"
    )
    print(f"✅ Created default role: ID {default_role.id}")

# If no employee types exist, create a default one
if not emp_types:
    print("\n🔧 Creating default employee type...")
    default_type = EmployeeType.objects.create(
        name="Full Time",
        description="Full-time employee"
    )
    print(f"✅ Created default employee type: ID {default_type.id}")

print("\n💡 Use these IDs when creating employees through the API.")
