from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from .models import Announcement
from .serializers import AnnouncementSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.utils.timezone import now
# Create your views here.

class AnnouncementViewset(ModelViewSet):
  queryset = Announcement.objects.all().order_by('end_date')
  serializer_class = AnnouncementSerializer
  permission_classes = [IsAuthenticated]

  def get_queryset(self):
    queryset = Announcement.objects.all()

    #  filter by active announcements only
    is_active = self.request.query_params.get('active')

    if is_active == 'true':
      today = now().date()
      queryset = queryset.filter(end_date__gte=today)

    return queryset.order_by('end_date')
  
  def check_permissions(self, request):
        super().check_permissions(request)
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            if not (request.user.is_staff or request.user.is_superuser):
                raise PermissionDenied("Only admin can create or delete announcements.")

