# test_fcm_notification.py
"""
Script to test Firebase Cloud Messaging notifications

Usage:
    python test_fcm_notification.py

This will send a test notification to all active FCM tokens in the database.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from notifications.models import FCMToken, Notification
from notifications.firebase import send_push_notification, send_multicast_notification
from django.contrib.auth import get_user_model

User = get_user_model()

def test_single_notification():
    """Send a test notification to the first active token"""
    print("🔍 Looking for active FCM tokens...")
    
    token = FCMToken.objects.filter(is_active=True).first()
    
    if not token:
        print("❌ No active FCM tokens found.")
        print("💡 Make sure to:")
        print("   1. Open the app in browser")
        print("   2. Click 'Enable Notifications'")
        print("   3. Grant permission")
        return
    
    print(f"✅ Found token for user: {token.user.username}")
    print(f"📱 Device: {token.device_name} ({token.device_type})")
    print(f"🔑 Token: {token.token[:30]}...")
    print()
    print("📤 Sending test notification...")
    
    result = send_push_notification(
        fcm_token=token.token,
        title="🎉 FCM Test Notification",
        body="Your Firebase Cloud Messaging setup is working perfectly!",
        data={
            "test": "true",
            "timestamp": str(timezone.now()),
            "message": "This is a test notification from Django backend"
        }
    )
    
    if result:
        print(f"✅ Notification sent successfully! Message ID: {result}")
        
        # Save to notification history
        Notification.objects.create(
            user=token.user,
            title="🎉 FCM Test Notification",
            body="Your Firebase Cloud Messaging setup is working perfectly!",
            notification_type="success",
            data={"test": "true"}
        )
        print("💾 Notification saved to database")
    else:
        print("❌ Failed to send notification")
        print("💡 Check:")
        print("   1. firebase-credentials.json is in the correct location")
        print("   2. Firebase project settings are correct")
        print("   3. Django logs for error details")

def test_multicast_notification():
    """Send a test notification to all active tokens"""
    print("🔍 Looking for active FCM tokens...")
    
    tokens = FCMToken.objects.filter(is_active=True)
    
    if not tokens.exists():
        print("❌ No active FCM tokens found.")
        print("💡 Make sure to:")
        print("   1. Open the app in browser")
        print("   2. Click 'Enable Notifications'")
        print("   3. Grant permission")
        return
    
    print(f"✅ Found {tokens.count()} active token(s)")
    for token in tokens:
        print(f"   - {token.user.username} ({token.device_type})")
    print()
    print("📤 Sending test notification to all devices...")
    
    token_list = list(tokens.values_list('token', flat=True))
    
    result = send_multicast_notification(
        fcm_tokens=token_list,
        title="🚀 ERMS Notification Test",
        body="This is a broadcast notification to all your devices!",
        data={
            "type": "test",
            "broadcast": "true",
            "message": "Multicast notification test"
        }
    )
    
    if result:
        print(f"✅ Notification sent!")
        print(f"   Success: {result.success_count} device(s)")
        print(f"   Failed: {result.failure_count} device(s)")
        
        # Save to notification history for all users
        for token in tokens:
            Notification.objects.create(
                user=token.user,
                title="🚀 ERMS Notification Test",
                body="This is a broadcast notification to all your devices!",
                notification_type="info",
                data={"type": "test", "broadcast": "true"}
            )
        print("💾 Notifications saved to database")
    else:
        print("❌ Failed to send notifications")

def test_user_specific_notification():
    """Send a notification to a specific user (interactive)"""
    print("🔍 Available users with FCM tokens:")
    print()
    
    users_with_tokens = User.objects.filter(fcm_tokens__is_active=True).distinct()
    
    if not users_with_tokens.exists():
        print("❌ No users with active FCM tokens found.")
        return
    
    for idx, user in enumerate(users_with_tokens, 1):
        token_count = user.fcm_tokens.filter(is_active=True).count()
        print(f"{idx}. {user.username} ({user.get_full_name()}) - {token_count} device(s)")
    
    print()
    try:
        choice = int(input("Enter user number to send notification (or 0 to skip): "))
        if choice == 0:
            return
        
        if choice < 1 or choice > users_with_tokens.count():
            print("❌ Invalid choice")
            return
        
        user = list(users_with_tokens)[choice - 1]
        tokens = FCMToken.objects.filter(user=user, is_active=True).values_list('token', flat=True)
        
        print(f"\n📤 Sending notification to {user.username}...")
        
        result = send_multicast_notification(
            fcm_tokens=list(tokens),
            title=f"👋 Hello {user.first_name}!",
            body="This is a personalized test notification just for you!",
            data={
                "user_id": str(user.id),
                "type": "personal_test"
            }
        )
        
        if result:
            print(f"✅ Sent to {result.success_count} device(s)")
            
            Notification.objects.create(
                user=user,
                title=f"👋 Hello {user.first_name}!",
                body="This is a personalized test notification just for you!",
                notification_type="info",
                data={"type": "personal_test"}
            )
            print("💾 Notification saved to database")
        else:
            print("❌ Failed to send notification")
            
    except ValueError:
        print("❌ Invalid input")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    from django.utils import timezone
    
    print("=" * 60)
    print("🔥 Firebase Cloud Messaging (FCM) Test Script")
    print("=" * 60)
    print()
    
    print("Select test type:")
    print("1. Send to first active token (quick test)")
    print("2. Send to all active tokens (broadcast)")
    print("3. Send to specific user (interactive)")
    print()
    
    try:
        choice = input("Enter your choice (1-3): ").strip()
        print()
        
        if choice == "1":
            test_single_notification()
        elif choice == "2":
            test_multicast_notification()
        elif choice == "3":
            test_user_specific_notification()
        else:
            print("❌ Invalid choice")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test cancelled")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 60)
    print("Test complete!")
    print("=" * 60)
