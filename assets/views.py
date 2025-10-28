from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
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
    queryset = Payment.objects.all().order_by('-created_at')
    serializer_class = PaymentSerializer
    
    def get_queryset(self):
        queryset = Payment.objects.all().order_by('-created_at')
        project_id = self.request.query_params.get('project', None)
        payment_type = self.request.query_params.get('type', None)
        
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
            
        return queryset
    


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

