#!/usr/bin/env python3
"""
Test employee creation with password to verify the fix
"""

import os
import sys
import django
import requests
import json
import random

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

django.setup()

from accounts.models import User

BASE_URL = "http://127.0.0.1:8000/api/v1"

print("🧪 Testing Employee Creation with Password")
print("=" * 60)

# Login as admin
print("1. Logging in as admin...")
login_response = requests.post(
    f"{BASE_URL}/accounts/login",
    json={"username": "admin", "password": "Admin@123"}
)

if login_response.status_code != 200:
    print(f"❌ Admin login failed: {login_response.status_code}")
    exit(1)

token = login_response.json().get('token')
headers = {"Authorization": f"Token {token}"}
print("✅ Admin login successful!")

# Create a test employee with password
print("\n2. Creating test employee with password...")
random_id = random.randint(1000, 9999)
test_employee = {
    "username": f"password_test_{random_id}",
    "password": "TestPassword@123",
    "first_name": "Password",
    "last_name": "Test",
    "email": "password.test@company.com",
    "phone": "9876543210",
    "employee_type": 1,
    "role": 4,
    "joining_date": "2024-01-15",
    "is_active": True
}

create_response = requests.post(
    f"{BASE_URL}/accounts/users/",
    headers=headers,
    json=test_employee
)

if create_response.status_code == 201:
    created_user = create_response.json()
    user_id = created_user['id']
    print(f"✅ Employee created successfully! ID: {user_id}")
    
    # Check if password was set correctly in database
    print("\n3. Checking password in database...")
    try:
        db_user = User.objects.get(id=user_id)
        has_password = bool(db_user.password)
        can_authenticate = db_user.check_password("TestPassword@123")
        
        print(f"   Has password in DB: {'✅' if has_password else '❌'}")
        print(f"   Password verification: {'✅' if can_authenticate else '❌'}")
        
        if has_password and can_authenticate:
            print("🎉 Password setting is working correctly!")
        else:
            print("❌ Password setting is still broken!")
            
    except User.DoesNotExist:
        print("❌ User not found in database!")
    
    # Test login with the new employee
    print("\n4. Testing login with new employee...")
    employee_login = requests.post(
        f"{BASE_URL}/accounts/login",
        json={
            "username": f"password_test_{random_id}",
            "password": "TestPassword@123"
        }
    )
    
    if employee_login.status_code == 200:
        print("✅ Employee login successful!")
        employee_token = employee_login.json().get('token')
        print(f"   Token received: {employee_token[:20]}...")
    else:
        print(f"❌ Employee login failed: {employee_login.status_code}")
        print(f"   Error: {employee_login.text}")
    
    # Clean up - delete test employee
    print("\n5. Cleaning up...")
    delete_response = requests.delete(
        f"{BASE_URL}/accounts/users/{user_id}/",
        headers=headers
    )
    if delete_response.status_code == 204:
        print("✅ Test employee deleted successfully!")
    else:
        print(f"⚠️ Failed to delete test employee: {delete_response.status_code}")

else:
    print(f"❌ Employee creation failed: {create_response.status_code}")
    print(f"   Error: {create_response.text}")

print("\n" + "=" * 60)
print("🏁 Test Complete!")
print("\n💡 If all tests passed, password setting is now working correctly.")
print("   You can create new employees and they will be able to login immediately.")
