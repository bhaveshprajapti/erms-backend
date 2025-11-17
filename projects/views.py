from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q, Sum, F, Case, When, DecimalField, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from .models import Project, Task, TimeLog, TaskComment
from .serializers import (
    ProjectSerializer, TaskSerializer, TimeLogSerializer, TaskCommentSerializer
)

# indrajit start

from .models import ProjectDetails,AmountPayable,AmountReceived
from .serializers import ProjectDetailSerializer,AmountPayableSerializer,AmountReceivedSerializer
from .utils import StandredResponse
from rest_framework.permissions import BasePermission, SAFE_METHODS
from datetime import datetime
from decimal import Decimal, InvalidOperation

# indrajit end

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
        
        # Calculate total expenses (sum of all expense fields with null handling)
        total_expense = projects.aggregate(
            total=Sum(
                Coalesce('other_expense', Value(0)) + 
                Coalesce('developer_charge', Value(0)) + 
                Coalesce('server_charge', Value(0)) + 
                Coalesce('third_party_api_charge', Value(0)) + 
                Coalesce('mediator_charge', Value(0)) + 
                Coalesce('domain_charge', Value(0)),
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

# indrajit start

class IsSuperUserOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.is_superuser

class ProjectDetailViewSet(StandredResponse,viewsets.ModelViewSet):
    queryset = ProjectDetails.objects.all().select_related('project')
    serializer_class = ProjectDetailSerializer

    def create(self,request,*args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return self.get_success_response(
            data=serializer.data, 
            message="Project Detail created successfully.",
            http_status=status.HTTP_201_CREATED
        )
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
            return self.get_success_response(
                data=paginated_data,
                message="Project Detail list retrieved successfully."
            )
            
        serializer = self.get_serializer(queryset, many=True)
        return self.get_success_response(
            data=serializer.data,
            message="Project Detail list retrieved successfully."
        )
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.get_success_response(
            data=serializer.data,
            message="Project Detail retrieved successfully."
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return self.get_success_response(
            data=serializer.data,
            message="Project Detail updated successfully."
        )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        
        # Delete mein koi data return nahi hota
        return self.get_success_response(
            data=None,
            message="Project Detail deleted successfully."
        )

class AmountPayableViewSet(StandredResponse, viewsets.ModelViewSet):
    queryset = AmountPayable.objects.all()
    serializer_class = AmountPayableSerializer

    permission_classes = [IsSuperUserOrReadOnly]

    # search_fields = [
    #     'title',
    #     'description',
    #     'paid_to_employee__username', # Assuming User model has 'username'
    #     'manual_paid_to_name'
    # ]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        employee_id_filter = request.query_params.get('employee_id')
        recipient_name_filter = request.query_params.get('employee_name')
        payment_mode_filter = request.query_params.get('payment_mode')
        start_date_filter = request.query_params.get('start_date') 
        end_date_filter = request.query_params.get('end_date')

        min_amount_filter = request.query_params.get('min_amount')
        max_amount_filter = request.query_params.get('max_amount')

        if employee_id_filter:
            queryset = queryset.filter(paid_to_employee_id=employee_id_filter)
          
        if recipient_name_filter:
            queryset = queryset.filter(
                Q(paid_to_employee__username__icontains=recipient_name_filter) | 
                Q(manual_paid_to_name__icontains=recipient_name_filter)
            )

        if payment_mode_filter:
            queryset = queryset.filter(payment_mode__iexact=payment_mode_filter)

        try:
            if min_amount_filter:
                min_amount = Decimal(min_amount_filter)
                queryset = queryset.filter(amount__gte=min_amount)
            
            if max_amount_filter:
                max_amount = Decimal(max_amount_filter)
                queryset = queryset.filter(amount__lte=max_amount)
        except InvalidOperation:
            return self.get_error_response(
                message="Invalid amount format for min_amount or max_amount.",
                http_status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if start_date_filter:
                start_date = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=start_date)
            
            if end_date_filter:
                end_date = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=end_date)
        except ValueError:
            # Date format galat hone par error response dein
            return self.get_error_response(
                message="Invalid date format. Please use YYYY-MM-DD for start_date and end_date.",
                http_status=status.HTTP_400_BAD_REQUEST
            )

        total_amount_sum = queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_id_count = queryset.count()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data

            response_data = {
                'total_expense': float(total_amount_sum),
                'total_id': total_id_count,
                'items': paginated_data 
            }
            
            return self.get_success_response(
                data=response_data,
                message="Amounts Payable list retrieved successfully with total."
            )
            
        serializer = self.get_serializer(queryset, many=True)

        response_data = {
            'total_expense': float(total_amount_sum),
            'total_id': total_id_count,
            'items': serializer.data 
        }

        return self.get_success_response(
            data=response_data,
            message="Amounts Payable list retrieved successfully with total."
        )
    
    @action(detail=False, methods=['get'])
    def mode_totals(self, request):
        # Group by payment_mode and calculate the sum and count for each group
        totals_by_mode = self.get_queryset().values('payment_mode').annotate(
            # Coalesce se null amount ko 0.0 consider kiya jayega
            total_amount=Coalesce(Sum('amount'), Value(0.0), output_field=DecimalField()),
            count=Count('id')
        )

        # Format the result (convert Decimal to float for JSON response)
        mode_breakdown = [
            {
                'payment_mode': item['payment_mode'],
                'total_expense': float(item['total_amount']),
                'count': item['count']
            }
            for item in totals_by_mode
        ]

        # Calculate overall grand total
        grand_total = self.get_queryset().aggregate(grand_total=Coalesce(Sum('amount'), Value(0.0), output_field=DecimalField()))['grand_total'] or Decimal('0')
        
        response_data = {
            'grand_total_all_modes': float(grand_total),
            'mode_breakdown': mode_breakdown
        }
        
        return self.get_success_response(
            data=response_data,
            message="Aggregated totals by payment mode retrieved successfully."
        )
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return self.get_success_response(
            data=serializer.data, 
            message="Amount Payable created successfully.",
            http_status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.get_success_response(
            data=serializer.data,
            message="Amount Payable retrieved successfully."
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return self.get_success_response(
            data=serializer.data,
            message="Amount Payable updated successfully."
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return self.get_success_response(
            data=None,
            message="Amount Payable deleted successfully."
        )

class AmountReceivedViewSet(StandredResponse, viewsets.ModelViewSet):
    queryset = AmountReceived.objects.all().select_related('client')
    serializer_class = AmountReceivedSerializer

    permission_classes = [IsSuperUserOrReadOnly]

    

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        client_filter = request.query_params.get('client_id')
        client_name_filter = request.query_params.get('client_name')
        payment_mode_filter = request.query_params.get('payment_mode')
        start_date_filter = request.query_params.get('start_date') 
        end_date_filter = request.query_params.get('end_date')

        min_amount_filter = request.query_params.get('min_amount')
        max_amount_filter = request.query_params.get('max_amount')

        if client_filter:
            queryset = queryset.filter(client_id=client_filter)
        if client_name_filter:
            queryset = queryset.filter(
                Q(client__name__icontains=client_name_filter) | 
                Q(manual_client_name__icontains=client_name_filter)
            )
        if payment_mode_filter:
            queryset = queryset.filter(payment_mode__iexact=payment_mode_filter)

        try:
            if min_amount_filter:
                min_amount = Decimal(min_amount_filter) 
                queryset = queryset.filter(amount__gte=min_amount)
            
            if max_amount_filter:
                max_amount = Decimal(max_amount_filter)
                queryset = queryset.filter(amount__lte=max_amount)
        except InvalidOperation:
            return self.get_error_response(
                message="Invalid amount format for min_amount or max_amount.",
                http_status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if start_date_filter:
                start_date = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=start_date)
            
            if end_date_filter:
                end_date = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=end_date)
        except ValueError:
            return self.get_error_response(
                message="Invalid date format. Please use YYYY-MM-DD for start_date and end_date.",
                http_status=status.HTTP_400_BAD_REQUEST
            )

        total_amount_sum = queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_id_count = queryset.count()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data

            response_data = {
                'total_income': float(total_amount_sum), 
                'total_id': total_id_count,
                'items': paginated_data 
            }
            
            return self.get_success_response(
                data=response_data,
                message="Amounts Received list retrieved successfully with total."
            )
            
        serializer = self.get_serializer(queryset, many=True)

        response_data = {
            'total_income': float(total_amount_sum),
            'total_id': total_id_count,
            'items': serializer.data 
        }

        return self.get_success_response(
            data=response_data,
            message="Amounts Received list retrieved successfully with total."
        )
    
    @action(detail=False, methods=['get'])
    def mode_totals(self, request):
        totals_by_mode = self.get_queryset().values('payment_mode').annotate(
            total_amount=Coalesce(Sum('amount'), Value(0.0), output_field=DecimalField()),
            count=Count('id')
        )

        mode_breakdown = [
            {
                'payment_mode': item['payment_mode'],
                'total_income': float(item['total_amount']), 
                'count': item['count']
            }
            for item in totals_by_mode
        ]

        grand_total = self.get_queryset().aggregate(grand_total=Coalesce(Sum('amount'), Value(0.0), output_field=DecimalField()))['grand_total'] or Decimal('0')
        
        response_data = {
            'grand_total_all_modes': float(grand_total),
            'mode_breakdown': mode_breakdown
        }
        
        return self.get_success_response(
            data=response_data,
            message="Aggregated totals by receipt mode retrieved successfully."
        )
   
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return self.get_success_response(
            data=serializer.data, 
            message="Amount Received created successfully.",
            http_status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.get_success_response(
            data=serializer.data,
            message="Amount Received retrieved successfully."
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return self.get_success_response(
            data=serializer.data,
            message="Amount Received updated successfully."
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return self.get_success_response(
            data=None,
            message="Amount Received deleted successfully."
        )


# indrajit end
    
