"""
Tests for session management and timeout functionality.
"""

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from attendance.models import SessionLog, Attendance

User = get_user_model()


class SessionManagementTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_session_log_creation(self):
        """Test that session logs are created properly"""
        session_log = SessionLog.log_event(
            user=self.user,
            event_type='login',
            notes='Test login'
        )
        
        self.assertEqual(session_log.user, self.user)
        self.assertEqual(session_log.event_type, 'login')
        self.assertTrue(session_log.is_session_active)
        self.assertIsNotNone(session_log.last_activity)
    
    def test_session_expiration_detection(self):
        """Test that session expiration is detected correctly"""
        # Create a session log with old activity
        old_time = timezone.now() - timedelta(hours=2)
        session_log = SessionLog.objects.create(
            user=self.user,
            event_type='login',
            date=timezone.now().date(),
            last_activity=old_time,
            is_session_active=True
        )
        
        # Check that session is expired
        self.assertTrue(session_log.is_session_expired())
    
    def test_session_not_expired(self):
        """Test that recent sessions are not expired"""
        # Create a recent session log
        recent_time = timezone.now() - timedelta(minutes=30)
        session_log = SessionLog.objects.create(
            user=self.user,
            event_type='login',
            date=timezone.now().date(),
            last_activity=recent_time,
            is_session_active=True
        )
        
        # Check that session is not expired
        self.assertFalse(session_log.is_session_expired())
    
    def test_get_active_session(self):
        """Test getting active session for a user"""
        # Create an active session
        session_log = SessionLog.log_event(
            user=self.user,
            event_type='login'
        )
        
        # Get active session
        active_session = SessionLog.get_active_session(self.user)
        self.assertEqual(active_session, session_log)
    
    def test_logout_deactivates_session(self):
        """Test that logout properly deactivates session"""
        # Create login session
        login_session = SessionLog.log_event(
            user=self.user,
            event_type='login'
        )
        
        # Create logout session
        logout_session = SessionLog.log_event(
            user=self.user,
            event_type='logout'
        )
        
        # Check that logout session is inactive
        logout_session.refresh_from_db()
        self.assertFalse(logout_session.is_session_active)
    
    def test_expired_session_cleanup(self):
        """Test that expired sessions are properly cleaned up"""
        # Create an attendance record
        attendance = Attendance.objects.create(
            user=self.user,
            date=timezone.now().date(),
            sessions=[{
                'check_in': timezone.now().isoformat(),
                'location_in': {'lat': 0, 'lng': 0}
            }]
        )
        
        # Create an expired session
        old_time = timezone.now() - timedelta(hours=2)
        expired_session = SessionLog.objects.create(
            user=self.user,
            event_type='login',
            date=timezone.now().date(),
            last_activity=old_time,
            is_session_active=True
        )
        
        # Run cleanup
        expired_count = SessionLog.check_and_handle_expired_sessions()
        
        # Check that session was processed
        self.assertEqual(expired_count, 1)
        
        # Check that session is now inactive
        expired_session.refresh_from_db()
        self.assertFalse(expired_session.is_session_active)
        
        # Check that attendance was auto-ended
        attendance.refresh_from_db()
        self.assertTrue(attendance.day_ended)
    
    def test_activity_update(self):
        """Test that session activity is updated properly"""
        session_log = SessionLog.log_event(
            user=self.user,
            event_type='login'
        )
        
        original_activity = session_log.last_activity
        
        # Wait a moment and update activity
        import time
        time.sleep(0.1)
        session_log.update_activity()
        
        # Check that activity was updated
        self.assertGreater(session_log.last_activity, original_activity)