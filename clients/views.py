from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.http import HttpResponse
from .models import Client, ClientRole, Quotation
from .serializers import (
    ClientSerializer, ClientListSerializer, ClientRoleSerializer, 
    QuotationSerializer, QuotationListSerializer
)
from .pdf_generator import generate_quotation_pdf


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.select_related('address', 'organization', 'status').order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ClientListSerializer
        return ClientSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def dropdown(self, request):
        """Get clients for dropdown selection"""
        clients = self.get_queryset().values('id', 'name', 'email')
        return Response(clients)


class ClientRoleViewSet(viewsets.ModelViewSet):
    queryset = ClientRole.objects.all().order_by('name')
    serializer_class = ClientRoleSerializer


class QuotationViewSet(viewsets.ModelViewSet):
    queryset = Quotation.objects.all().select_related('client', 'status').order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return QuotationListSerializer
        return QuotationSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by client
        client_id = self.request.query_params.get('client', None)
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        
        # Filter by status
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status__name=status_param)
        
        # Search in quotation number, title, or client info
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(quotation_no__icontains=search) |
                Q(title__icontains=search) |
                Q(client__name__icontains=search) |
                Q(client_name__icontains=search)
            )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def link_client(self, request, pk=None):
        """Link an existing client to a quotation"""
        quotation = self.get_object()
        client_id = request.data.get('client_id')
        
        if not client_id:
            return Response(
                {'error': 'client_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            client = Client.objects.get(id=client_id)
            quotation.client = client
            # Clear standalone client fields when linking
            quotation.client_name = None
            quotation.client_email = None
            quotation.client_phone = None
            quotation.client_address = None
            quotation.save()
            
            serializer = self.get_serializer(quotation)
            return Response(serializer.data)
        
        except Client.DoesNotExist:
            return Response(
                {'error': 'Client not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """Generate and download quotation as PDF"""
        quotation = self.get_object()
        
        try:
            # Generate PDF
            pdf_buffer = generate_quotation_pdf(quotation)
            
            # Create HTTP response with PDF
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Quotation_{quotation.quotation_no}.pdf"'
            return response
        
        except Exception as e:
            return Response(
                {'error': f'Failed to generate PDF: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def unlink_client(self, request, pk=None):
        """Unlink client from quotation (make it standalone)"""
        quotation = self.get_object()
        
        if quotation.client:
            # Store client info in standalone fields before unlinking
            quotation.client_name = quotation.client.name
            quotation.client_email = quotation.client.email
            quotation.client_phone = quotation.client.phone
            quotation.client_address = str(quotation.client.address) if quotation.client.address else None
            quotation.client = None
            quotation.save()
        
        serializer = self.get_serializer(quotation)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='next-number')
    def next_number(self, request):
        """Generate next quotation number in format: QT-DW-DDMMYYYY-XXXXXX"""
        from .utils import ensure_unique_quotation_number
        
        quotation_no = ensure_unique_quotation_number()
        
        return Response({
            'quotation_no': quotation_no
        })
    
    @action(detail=True, methods=['post'])
    def convert_to_project(self, request, pk=None):
        """Convert quotation to project (placeholder for future implementation)"""
        quotation = self.get_object()
        
        # This would create a project based on the quotation
        # For now, just mark as converted
        quotation.is_converted = True
        quotation.save()
        
        return Response({
            'message': 'Quotation marked as converted',
            'quotation_id': quotation.id
        })

