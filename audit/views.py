from rest_framework import viewsets
from .models import AuditLog
from .serializers import AuditLogSerializer

class AuditLogViewSet(viewsets.ModelViewSet):
    queryset = AuditLog.objects.all().order_by('-created_at')
    serializer_class = AuditLogSerializer

