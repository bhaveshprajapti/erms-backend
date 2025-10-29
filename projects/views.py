from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q, Sum, F, Case, When, DecimalField
from decimal import Decimal
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
    
    @action(detail=False, methods=['get'])
    def profit_loss_stats(self, request):
        """Get profit & loss statistics for P&L dashboard"""
        from assets.models import Payment
        
        projects = self.queryset.all()
        
        # Calculate totals
        total_projects = projects.count()
        
        # Calculate total income from actual payments received
        total_income = Payment.objects.filter(
            project__isnull=False
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # Calculate total expenses (sum of all expense fields)
        total_expense = projects.aggregate(
            total=Sum(
                F('other_expense') + 
                F('developer_charge') + 
                F('server_charge') + 
                F('third_party_api_charge') + 
                F('mediator_charge') + 
                F('domain_charge'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )['total'] or Decimal('0')
        
        # Calculate net profit
        net_profit = total_income - total_expense
        
        return Response({
            'total_projects': total_projects,
            'total_income': float(total_income),
            'total_expense': float(total_expense),
            'net_profit': float(net_profit),
        })
    
    @action(detail=False, methods=['get'])
    def profit_loss_list(self, request):
        """Get project list with profit/loss calculations for P&L table"""
        from assets.models import Payment
        
        projects = self.queryset.select_related('quotation').prefetch_related(
            'technologies', 'app_mode', 'team_members'
        )
        
        # Add calculated fields
        projects_data = []
        for project in projects:
            # Calculate total expenses
            total_expenses = (
                (project.other_expense or 0) +
                (project.developer_charge or 0) +
                (project.server_charge or 0) +
                (project.third_party_api_charge or 0) +
                (project.mediator_charge or 0) +
                (project.domain_charge or 0)
            )
            
            # Calculate actual income from payments received
            received_payments = Payment.objects.filter(
                project=project
            ).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            
            # Calculate profit/loss
            profit_loss = received_payments - total_expenses
            
            # Calculate duration
            duration = None
            if project.start_date and project.deadline:
                delta = project.deadline - project.start_date
                duration = f"{delta.days} days"
            elif project.start_date and project.completed_date:
                delta = project.completed_date - project.start_date
                duration = f"{delta.days} days"
            
            projects_data.append({
                'id': project.id,
                'project_id': project.project_id,
                'project_name': project.project_name,
                'duration': duration,
                'income': float(received_payments),
                'expense': float(total_expenses),
                'profit_loss': float(profit_loss),
                'status': project.status,
                'start_date': project.start_date,
                'deadline': project.deadline,
                'completed_date': project.completed_date,
            })
        
        return Response(projects_data)

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

class TimeLogViewSet(viewsets.ModelViewSet):
    queryset = TimeLog.objects.all()
    serializer_class = TimeLogSerializer

class TaskCommentViewSet(viewsets.ModelViewSet):
    queryset = TaskComment.objects.all()
    serializer_class = TaskCommentSerializer

