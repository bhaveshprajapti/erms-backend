import os
import django
import sys
import json

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from common.models import Address
from common.views import AddressViewSet
from rest_framework.test import APIRequestFactory

def test_address_view():
    print("--- Testing AddressViewSet ---")
    
    # 1. Get an existing address
    address = Address.objects.first()
    if not address:
        print("No address found, creating one.")
        address = Address.objects.create(line1="123 Test St", type="current")
        
    print(f"Testing with Address ID: {address.id}")
    
    # 2. Simulate API request
    factory = APIRequestFactory()
    request = factory.get(f'/common/addresses/{address.id}/')
    view = AddressViewSet.as_view({'get': 'retrieve'})
    
    try:
        response = view(request, pk=address.id)
        print(f"Response Status: {response.status_code}")
        print(f"Response Data: {json.dumps(response.data, indent=2, default=str)}")
        
        if response.status_code == 200 and response.data.get('line1') == address.line1:
            print("SUCCESS: AddressViewSet returns correct data.")
        else:
            print("FAILURE: AddressViewSet returned unexpected data.")
            
    except Exception as e:
        print(f"ERROR: View raised exception: {e}")

if __name__ == "__main__":
    test_address_view()
