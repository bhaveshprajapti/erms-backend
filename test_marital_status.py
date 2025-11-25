import os
import django
import sys
import json

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User
from accounts.serializers import UserDetailSerializer

def test_marital_status():
    print("--- Testing Marital Status Field ---")
    
    # Get a user with marital status
    users = User.objects.filter(marital_status__isnull=False).exclude(marital_status='')
    
    if not users.exists():
        print("No users with marital_status found. Creating test user...")
        user = User.objects.create_user(
            username="test_marital",
            password="password",
            first_name="Test",
            last_name="User",
            marital_status="married"
        )
    else:
        user = users.first()
    
    print(f"Testing with user: {user.username}")
    print(f"Database marital_status value: '{user.marital_status}'")
    print(f"Type: {type(user.marital_status)}")
    
    # Serialize
    serializer = UserDetailSerializer(user)
    data = serializer.data
    
    print(f"\nSerialized marital_status: '{data.get('marital_status')}'")
    print(f"Type: {type(data.get('marital_status'))}")
    
    # Check all personal fields
    print("\n--- All Personal Fields ---")
    personal_fields = ['first_name', 'last_name', 'gender', 'birth_date', 'marital_status']
    for field in personal_fields:
        value = data.get(field)
        print(f"{field}: '{value}' (type: {type(value).__name__})")

if __name__ == "__main__":
    test_marital_status()
