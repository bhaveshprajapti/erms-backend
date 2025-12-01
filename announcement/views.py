from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from .models import Announcement
from .serializers import AnnouncementSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.utils.timezone import now
import logging

logger = logging.getLogger(__name__)

# Create your views here.

class AnnouncementViewset(ModelViewSet):
  queryset = Announcement.objects.all().order_by('-created_at')
  serializer_class = AnnouncementSerializer
  permission_classes = [IsAuthenticated]

  def get_queryset(self):
    queryset = Announcement.objects.all()

    #  filter by active announcements only
    is_active = self.request.query_params.get('active')

    if is_active == 'true':
      today = now().date()
      queryset = queryset.filter(end_date__gte=today)

    # Order by created_at descending (latest first)
    return queryset.order_by('-created_at')
  
  def check_permissions(self, request):
        super().check_permissions(request)
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            if not (request.user.is_staff or request.user.is_superuser):
                raise PermissionDenied("Only admin can create or delete announcements.")
  
  def perform_create(self, serializer):
        """Send notification when a new active announcement is created"""
        announcement = serializer.save()
        
        # Check if announcement is currently active
        today = now().date()
        logger.info(f"Announcement created: {announcement.title}, start_date={announcement.start_date}, end_date={announcement.end_date}, today={today}")
        
        if announcement.start_date <= today <= announcement.end_date:
            logger.info(f"Announcement is active, sending notification...")
            try:
                from notifications.services import NotificationService
                # Exclude the admin who created the announcement
                result = NotificationService.notify_announcement(announcement, exclude_user=self.request.user)
                logger.info(f"Notification result for announcement '{announcement.title}': {result}")
            except Exception as e:
                logger.error(f"Failed to send notification for announcement: {e}", exc_info=True)
        else:
            logger.info(f"Announcement is not active yet (start_date={announcement.start_date}, today={today}), skipping notification")
  
  def perform_update(self, serializer):
        """Send notification if announcement becomes active after update"""
        old_instance = self.get_object()
        today = now().date()
        was_active = old_instance.start_date <= today <= old_instance.end_date
        
        announcement = serializer.save()
        is_active = announcement.start_date <= today <= announcement.end_date
        
        # Send notification if announcement just became active
        if is_active and not was_active:
            try:
                from notifications.services import NotificationService
                # Exclude the admin who updated the announcement
                NotificationService.notify_announcement(announcement, exclude_user=self.request.user)
                logger.info(f"Notification sent for activated announcement: {announcement.title}")
            except Exception as e:
                logger.error(f"Failed to send notification for announcement: {e}")

