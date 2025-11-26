from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuotationViewSet, QuotationHTMLView

router = DefaultRouter()
router.register(r'', QuotationViewSet, basename='quotation')

from .views import test_quotation_view

urlpatterns = [
    path('', include(router.urls)),
    path('view/', QuotationHTMLView.as_view(), name='quotation-html-view'),
    path('view/<int:quotation_id>/', QuotationHTMLView.as_view(), name='quotation-html-view-with-id'),
    path('test/', test_quotation_view, name='quotation-test'),
]