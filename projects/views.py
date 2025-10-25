from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from .models import Project, Task, TimeLog, TaskComment
from .serializers import (
    ProjectSerializer, TaskSerializer, TimeLogSerializer, TaskCommentSerializer
)

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().prefetch_related('technologies', 'app_mode', 'team_members').select_related('quotation')
    serializer_class = ProjectSerializer
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get project statistics for dashboard cards"""
        total_projects = self.queryset.count()
        in_progress = self.queryset.filter(status='In Progress').count()
        completed = self.queryset.filter(status='Completed').count()
        on_hold = self.queryset.filter(status='On Hold').count()
        
        return Response({
            'total_projects': total_projects,
            'in_progress': in_progress,
            'completed': completed,
            'on_hold': on_hold,
        })

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

class TimeLogViewSet(viewsets.ModelViewSet):
    queryset = TimeLog.objects.all()
    serializer_class = TimeLogSerializer

class TaskCommentViewSet(viewsets.ModelViewSet):
    queryset = TaskComment.objects.all()
    serializer_class = TaskCommentSerializer

