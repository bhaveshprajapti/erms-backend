from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DirectoryViewSet, FolderViewSet, FileDocumentViewSet,
    ExpenseViewSet, PaymentViewSet, SalaryRecordViewSet
)

router = DefaultRouter()
router.register(r'directories', DirectoryViewSet)
router.register(r'folders', FolderViewSet)
router.register(r'documents', FileDocumentViewSet)
router.register(r'expenses', ExpenseViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'salary-records', SalaryRecordViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
