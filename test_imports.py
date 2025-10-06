#!/usr/bin/env python3
"""
Test imports to identify the issue
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
    print("✅ Django setup successful")
    
    # Test importing accounts models
    print("Testing accounts models import...")
    from accounts.models import User, Organization, Role, ProfileUpdateRequest
    print("✅ Accounts models imported successfully")
    
    # Test importing common models
    print("Testing common models import...")
    from common.models import Address, EmployeeType, Designation, Technology, Shift
    print("✅ Common models imported successfully")
    
    # Test importing accounts serializers
    print("Testing accounts serializers import...")
    from accounts.serializers import ProfileUpdateRequestSerializer
    print("✅ Accounts serializers imported successfully")
    
    print("🎉 All imports successful!")
    
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
