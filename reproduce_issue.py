import os
import django
import sys
import json

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User
from common.models import Address
from accounts.serializers import UserDetailSerializer

def reproduce():
    print("--- Starting Reproduction Script (Reverted State) ---")
    
    # 1. Create a test user with an address
    username = "test_user_repro"
    
    try:
        user = User.objects.get(username=username)
        print(f"Found existing user {user.username}")
    except User.DoesNotExist:
        print("User not found, creating...")
        user = User.objects.create_user(username=username, password="password")
        address = Address.objects.create(line1="123 Test St", type="current")
        user.current_address = address
        user.save()
    
    # 2. Serialize the user
    serializer = UserDetailSerializer(user)
    data = serializer.data
    
    print("--- Serialized Data (Address Field) ---")
    print(f"current_address: {data.get('current_address')}")
    
    if isinstance(data.get('current_address'), int):
        print("CONFIRMED: Serializer returns Address ID.")
    else:
        print(f"UNEXPECTED: Serializer returns {type(data.get('current_address'))}")

if __name__ == "__main__":
    reproduce()
