import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User

def migrate_marital_status():
    """
    Migrate marital_status from 'single' to 'unmarried' to standardize values.
    """
    print("--- Migrating Marital Status Values ---")
    
    # Find all users with 'single' marital status
    users_with_single = User.objects.filter(marital_status='single')
    count = users_with_single.count()
    
    print(f"Found {count} users with marital_status='single'")
    
    if count > 0:
        # Update to 'unmarried'
        updated = users_with_single.update(marital_status='unmarried')
        print(f"Updated {updated} users from 'single' to 'unmarried'")
        
        # Verify
        remaining = User.objects.filter(marital_status='single').count()
        if remaining == 0:
            print("✓ Migration successful! No 'single' values remaining.")
        else:
            print(f"⚠ Warning: {remaining} 'single' values still remain.")
    else:
        print("No migration needed. No users with 'single' status found.")
    
    # Show current distribution
    print("\n--- Current Marital Status Distribution ---")
    from django.db.models import Count
    distribution = User.objects.exclude(marital_status__isnull=True).exclude(marital_status='').values('marital_status').annotate(count=Count('id'))
    for item in distribution:
        print(f"{item['marital_status']}: {item['count']} users")

if __name__ == "__main__":
    migrate_marital_status()
