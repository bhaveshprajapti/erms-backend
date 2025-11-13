from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q
from .models import (
    Directory, Folder, FileDocument, Expense, Payment, SalaryRecord
)
from .serializers import (
    DirectorySerializer, FolderSerializer, FileDocumentSerializer, 
    ExpenseSerializer, PaymentSerializer, SalaryRecordSerializer
)

class DirectoryViewSet(viewsets.ModelViewSet):
    queryset = Directory.objects.all().order_by('-created_at')
    serializer_class = DirectorySerializer

class FolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.all().order_by('-created_at')
    serializer_class = FolderSerializer

class FileDocumentViewSet(viewsets.ModelViewSet):
    queryset = FileDocument.objects.all().order_by('-created_at')
    serializer_class = FileDocumentSerializer

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all().order_by('-created_at')
    serializer_class = ExpenseSerializer

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().order_by('-date', '-created_at')  # Order by payment date first, then created_at
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """
        Allow sub-admin (staff) and admin (superuser) to perform CRUD operations
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Only staff and superuser can create, update, delete
            return [IsAuthenticated()]
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        """Override to add any additional logic during creation"""
        serializer.save()
    
    def perform_update(self, serializer):
        """Override to add any additional logic during update"""
        serializer.save()
    
    def perform_destroy(self, instance):
        """Override to add any additional logic during deletion"""
        instance.delete()
    
    def get_queryset(self):
        queryset = Payment.objects.all().order_by('-date', '-created_at')  # Order by payment date first
        project_id = self.request.query_params.get('project', None)
        payment_type = self.request.query_params.get('type', None)
        consolidate = self.request.query_params.get('consolidate', None)
        
        if project_id is not None and project_id != '':
            try:
                project_id = int(project_id)
                queryset = queryset.filter(project_id=project_id)
            except (ValueError, TypeError):
                # Invalid project_id, ignore the filter
                pass
            
        # Filter by payment type
        if payment_type == 'from-client':
            # Payments from clients (income) - no specific recipient (company receives)
            queryset = queryset.filter(recipient__isnull=True)
        elif payment_type == 'to-developers':
            # Payments to developers (expenses) - have specific recipients
            queryset = queryset.filter(recipient__isnull=False)
        
        # If consolidate is requested, return one payment per project (latest one)
        if consolidate == 'true' and payment_type == 'from-client':
            # Get unique project IDs and return the latest payment for each project
            from django.db.models import Max
            
            # Get the latest payment for each project
            project_payments = queryset.values('project').annotate(
                latest_id=Max('id')
            )
            
            # Build a list of payment IDs to include (one per project)
            payment_ids = [p['latest_id'] for p in project_payments if p['latest_id']]
            
            queryset = queryset.filter(id__in=payment_ids)
            
        return queryset
    


    @action(detail=False, methods=['get'])
    def consolidated(self, request):
        """Get consolidated payments by project"""
        payment_type = self.request.query_params.get('type', None)
        
        if payment_type != 'from-client':
            return Response([])
        
        # Get all client payments
        payments = Payment.objects.filter(recipient__isnull=True).order_by('-date', '-created_at')
        
        # Group by project and create consolidated entries
        from django.db.models import Sum, Max
        from collections import defaultdict
        
        consolidated_data = []
        
        # Get project-wise aggregated data
        project_aggregates = payments.values('project').annotate(
            total_amount=Sum('amount'),
            latest_date=Max('date'),
            latest_method=Max('method'),
            latest_id=Max('id')
        ).order_by('-latest_id')
        
        for aggregate in project_aggregates:
            project_id = aggregate['project']
            
            # Get the latest payment for this project to use as base
            if project_id is None:
                latest_payment = payments.filter(
                    project__isnull=True,
                    id=aggregate['latest_id']
                ).first()
            else:
                latest_payment = payments.filter(
                    project_id=project_id,
                    id=aggregate['latest_id']
                ).first()
            
            if latest_payment:
                try:
                    # Create consolidated payment data
                    consolidated_payment = {
                        'id': latest_payment.id,
                        'project': {
                            'id': latest_payment.project.id if latest_payment.project else None,
                            'project_id': latest_payment.project.project_id if latest_payment.project else 'General',
                            'project_name': latest_payment.project.project_name if latest_payment.project else 'General Payment'
                        } if latest_payment.project else None,
                        'recipient': None,
                        'amount': float(aggregate['total_amount']),
                        'total_received': float(aggregate['total_amount']),
                        'date': aggregate['latest_date'].isoformat() if aggregate['latest_date'] else None,
                        'method': aggregate['latest_method'] or '',
                        'details': latest_payment.details,
                        'status': {
                            'id': latest_payment.status.id if latest_payment.status else None,
                            'name': latest_payment.status.name if latest_payment.status else None
                        } if latest_payment.status else None,
                        'created_at': latest_payment.created_at.isoformat() if latest_payment.created_at else None
                    }
                    
                    # Calculate computed status and remaining amount
                    if latest_payment.project:
                        approval_amount = float(latest_payment.project.approval_amount or 0)
                        total_received = float(aggregate['total_amount'])
                        remaining_amount = max(0, approval_amount - total_received)
                        
                        consolidated_payment['remaining_amount'] = remaining_amount
                        
                        # Compute status
                        if approval_amount == 0:
                            status_name = 'Advanced'
                        elif total_received >= approval_amount:
                            status_name = 'Received'
                        elif total_received > 0:
                            status_name = 'Advanced'
                        else:
                            status_name = 'Pending'
                        
                        consolidated_payment['computed_status'] = {
                            'id': None,
                            'name': status_name
                        }
                    else:
                        consolidated_payment['remaining_amount'] = None
                        consolidated_payment['computed_status'] = {
                            'id': None,
                            'name': 'Pending'
                        }
                    
                    consolidated_data.append(consolidated_payment)
                except Exception as e:
                    # Skip this payment if there's an error
                    continue
        
        return Response(consolidated_data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get payment statistics"""
        payments = Payment.objects.all()
        payment_type = self.request.query_params.get('type', None)
        
        # Filter by payment type
        if payment_type == 'from-client':
            # Payments from clients (income) - no specific recipient (company receives)
            payments = payments.filter(recipient__isnull=True)
        elif payment_type == 'to-developers':
            # Payments to developers (expenses) - have specific recipients
            payments = payments.filter(recipient__isnull=False)
        
        # Total payments and amount
        total_stats = payments.aggregate(
            total_count=Count('id'),
            total_amount=Sum('amount')
        )
        
        # Bank Transfer stats
        bank_stats = payments.filter(method__icontains='bank').aggregate(
            count=Count('id'),
            amount=Sum('amount')
        )
        
        # UPI stats
        upi_stats = payments.filter(method__icontains='upi').aggregate(
            count=Count('id'),
            amount=Sum('amount')
        )
        
        # Cash stats
        cash_stats = payments.filter(method__icontains='cash').aggregate(
            count=Count('id'),
            amount=Sum('amount')
        )
        
        # Cheque stats
        cheque_stats = payments.filter(method__icontains='cheque').aggregate(
            count=Count('id'),
            amount=Sum('amount')
        )
        
        return Response({
            'totalPayments': total_stats['total_count'] or 0,
            'totalAmount': float(total_stats['total_amount'] or 0),
            'bankTransfer': bank_stats['count'] or 0,
            'bankTransferAmount': float(bank_stats['amount'] or 0),
            'upi': upi_stats['count'] or 0,
            'upiAmount': float(upi_stats['amount'] or 0),
            'cash': cash_stats['count'] or 0,
            'cashAmount': float(cash_stats['amount'] or 0),
            'cheque': cheque_stats['count'] or 0,
            'chequeAmount': float(cheque_stats['amount'] or 0),
        })

class SalaryRecordViewSet(viewsets.ModelViewSet):
    queryset = SalaryRecord.objects.all().order_by('-created_at')
    serializer_class = SalaryRecordSerializer

