from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import os
from django.conf import settings
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
            # Try HTML-based PDF generator first (better quality, pixel-perfect)
            try:
                from .html_pdf_generator import generate_quotation_html_pdf
                pdf_buffer = generate_quotation_html_pdf(quotation)
                print("Using WeasyPrint HTML PDF generator")
            except (ImportError, OSError) as e:
                # Fallback to simple ReportLab generator if WeasyPrint not available or fails
                print(f"WeasyPrint not available or failed, using simple ReportLab generator: {e}")
                try:
                    from .simple_pdf_generator import generate_simple_quotation_pdf
                    pdf_buffer = generate_simple_quotation_pdf(quotation)
                except ImportError:
                    # Final fallback to original ReportLab generator
                    print("Using original ReportLab generator")
                    pdf_buffer = generate_quotation_pdf(quotation)
            
            # Create HTTP response with PDF
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Quotation_{quotation.quotation_no}.pdf"'
            return response
        
        except Exception as e:
            import traceback
            traceback.print_exc()
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


class QuotationHTMLView(View):
    """Serve the quotation HTML page with dynamic data"""
    
    def get(self, request, quotation_id=None):
        # Read the HTML file
        html_file_path = os.path.join(settings.BASE_DIR, 'quotation.html')
        
        try:
            with open(html_file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            
            # If quotation_id is provided, we could inject the data
            if quotation_id:
                try:
                    quotation = get_object_or_404(Quotation, id=quotation_id)
                    # Inject quotation data into the HTML
                    html_content = self.inject_quotation_data(html_content, quotation)
                except Quotation.DoesNotExist:
                    pass
            
            return HttpResponse(html_content, content_type='text/html')
            
        except FileNotFoundError:
            return HttpResponse(
                '<h1>Quotation template not found</h1><p>Please ensure quotation.html exists in the project root.</p>',
                status=404
            )
    
    def inject_quotation_data(self, html_content, quotation):
        """Inject quotation data into HTML template"""
        import json
        from datetime import datetime
        
        # Prepare quotation data
        client_info = quotation.get_client_info()
        
        # Format dates
        def format_date(date_obj):
            if not date_obj:
                return "N/A"
            return date_obj.strftime('%d %B, %Y')
        
        # Prepare service items
        service_items = quotation.service_items if quotation.service_items else []
        
        # Calculate hosting charges
        server_charge = 0
        domain_charge = 0
        
        if quotation.server_hosting and isinstance(quotation.server_hosting, dict):
            if quotation.server_hosting.get('included', False):
                server_charge = quotation.server_hosting.get('unit_price', 0)
        
        if quotation.domain_registration and isinstance(quotation.domain_registration, dict):
            if quotation.domain_registration.get('included', False):
                domain_charge = quotation.domain_registration.get('unit_price', 0)
        
        quotation_data = {
            'quotation_no': quotation.quotation_no,
            'client_name': client_info.get('name', 'N/A'),
            'client_email': client_info.get('email', ''),
            'client_phone': client_info.get('phone', ''),
            'client_address': client_info.get('address', ''),
            'date': format_date(quotation.date),
            'valid_until': format_date(quotation.valid_until),
            'service_items': service_items,
            'subtotal': float(quotation.subtotal or 0),
            'tax_amount': float(quotation.tax_amount or 0),
            'server_hosting': {
                'included': bool(server_charge),
                'unit_price': server_charge
            },
            'domain_registration': {
                'included': bool(domain_charge),
                'unit_price': domain_charge
            },
            'grand_total': float(quotation.grand_total or 0),
            'terms_conditions': quotation.terms_conditions.split('\n') if quotation.terms_conditions else [],
            'signatory_name': quotation.signatory_name or 'CEO Naman Doshi',
            'additional_notes': quotation.additional_notes or ''
        }
        
        # Inject data into HTML
        data_script = f"""
        <script>
            // Auto-load quotation data
            document.addEventListener('DOMContentLoaded', function() {{
                const quotationData = {json.dumps(quotation_data)};
                if (window.quotationManager) {{
                    window.quotationManager.loadQuotationData(quotationData);
                }}
            }});
        </script>
        """
        
        # Insert the script before closing body tag
        html_content = html_content.replace('</body>', f'{data_script}</body>')
        
        return html_content


def test_quotation_view(request):
    """Test view to serve the quotation HTML page"""
    from django.http import HttpResponse
    import os
    from django.conf import settings
    
    html_file_path = os.path.join(settings.BASE_DIR, 'quotation.html')
    
    try:
        with open(html_file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        return HttpResponse(html_content, content_type='text/html')
    except FileNotFoundError:
        return HttpResponse(
            '<h1>Quotation template not found</h1><p>Please ensure quotation.html exists in the project root.</p>',
            status=404
        )

