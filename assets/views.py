from rest_framework import viewsets
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

class SalaryRecordViewSet(viewsets.ModelViewSet):
    queryset = SalaryRecord.objects.all().order_by('-created_at')
    serializer_class = SalaryRecordSerializer

