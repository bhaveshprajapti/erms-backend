#!/usr/bin/env python3
"""
Test password setting directly using Django ORM
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

django.setup()

from accounts.models import User
from accounts.serializers import UserDetailSerializer

print("🧪 Testing Password Setting Directly")
print("=" * 50)

# Test 1: Direct Django User creation
print("1. Testing direct Django User creation...")
test_user = User.objects.create_user(
    username="direct_test_user",
    password="DirectTest@123",
    email="direct@test.com"
)
print(f"✅ User created: {test_user.username}")
print(f"   Has password: {'✅' if test_user.password else '❌'}")
print(f"   Can authenticate: {'✅' if test_user.check_password('DirectTest@123') else '❌'}")

# Clean up
test_user.delete()
print("🗑️ Direct test user deleted")

# Test 2: Using serializer directly
print("\n2. Testing UserDetailSerializer directly...")
serializer_data = {
    'username': 'serializer_test_user',
    'password': 'SerializerTest@123',
    'first_name': 'Serializer',
    'last_name': 'Test',
    'email': 'serializer@test.com',
    'employee_type': 1,
    'role': 4,
    'is_active': True
}

serializer = UserDetailSerializer(data=serializer_data)
if serializer.is_valid():
    print("✅ Serializer validation passed")
    instance = serializer.save()
    print(f"✅ User created via serializer: {instance.username}")
    print(f"   Has password: {'✅' if instance.password else '❌'}")
    print(f"   Can authenticate: {'✅' if instance.check_password('SerializerTest@123') else '❌'}")
    
    # Clean up
    instance.delete()
    print("🗑️ Serializer test user deleted")
else:
    print("❌ Serializer validation failed:")
    print(serializer.errors)

print("\n" + "=" * 50)
print("🏁 Direct Test Complete!")
print("\nThis test bypasses the API to check if the serializer itself works correctly.")
