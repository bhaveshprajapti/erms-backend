"""
Simple PDF generator for quotations using ReportLab
This is a fallback when WeasyPrint is not available
"""
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


def format_date(date_obj):
    """Format date to '22 August, 2025' format"""
    if not date_obj:
        return "N/A"
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
        except:
            return date_obj
    return date_obj.strftime('%d %B, %Y')


def format_currency(amount):
    """Format currency with RS prefix"""
    if amount is None:
        return "₹0"
    return f"₹{amount:,.2f}"


def generate_simple_quotation_pdf(quotation):
    """
    Generate PDF using ReportLab for quotation
    Returns BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#052455')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor('#052455')
    )
    
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    
    # Build content
    content = []
    
    # Company Header
    header_data = [
        ['DIGIWAVE TECHNOLOGIES', ''],
        ['', '401 medani jain hostel, navjivan press road,\nincome tax cross road, Ahmedabad,\ngujarat, india-380009']
    ]
    
    header_table = Table(header_data, colWidths=[4*inch, 3*inch])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, 0), 20),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor('#052455')),
        ('FONTSIZE', (1, 1), (1, 1), 8),
        ('ALIGN', (1, 1), (1, 1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    content.append(header_table)
    content.append(Spacer(1, 20))
    
    # Title
    content.append(Paragraph("QUOTATION", title_style))
    
    # Quotation details
    quotation_no = getattr(quotation, 'quotation_no', 'N/A')
    content.append(Paragraph(f"#{quotation_no}", styles['Normal']))
    content.append(Spacer(1, 20))
    
    # Date and client info
    date_info = f"<b>Date:</b> {format_date(getattr(quotation, 'date', None))}<br/>"
    date_info += f"<b>Valid Until:</b> {format_date(getattr(quotation, 'valid_until', None))}"
    
    client_name = getattr(quotation, 'client_name', 'N/A')
    client_email = getattr(quotation, 'client_email', '')
    client_phone = getattr(quotation, 'client_phone', '')
    client_address = getattr(quotation, 'client_address', '')
    
    client_info = f"<b>To:</b><br/>{client_name}"
    if client_email:
        client_info += f"<br/>{client_email}"
    if client_phone:
        client_info += f"<br/>{client_phone}"
    if client_address:
        client_info += f"<br/>{client_address}"
    
    info_data = [
        [Paragraph(date_info, normal_style), Paragraph(client_info, normal_style)]
    ]
    
    info_table = Table(info_data, colWidths=[3.5*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    content.append(info_table)
    content.append(Spacer(1, 20))
    
    # Horizontal line
    content.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    content.append(Spacer(1, 20))
    
    # Service items table
    service_items = getattr(quotation, 'service_items', [])
    if isinstance(service_items, str):
        import json
        try:
            service_items = json.loads(service_items)
        except:
            service_items = []
    
    # Table headers
    table_data = [
        ['Service Description', 'Qty', 'Unit Price', 'Discount', 'Tax', 'Line Total']
    ]
    
    # Add service items
    subtotal = 0
    for item in service_items[:5]:  # Limit to 5 items for space
        description = item.get('description', 'N/A')
        quantity = item.get('quantity', 0)
        unit_price = item.get('unit_price', 0)
        discount = item.get('discount', 0)
        tax_rate = item.get('tax_rate', 0)
        line_total = (quantity * unit_price) - discount
        subtotal += line_total
        
        table_data.append([
            description,
            str(quantity),
            format_currency(unit_price),
            format_currency(discount) if discount else '-',
            f"{tax_rate}%" if tax_rate else '-',
            format_currency(line_total)
        ])
    
    # Create table
    items_table = Table(table_data, colWidths=[2.5*inch, 0.5*inch, 1*inch, 0.8*inch, 0.5*inch, 1*inch])
    items_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3FFFF')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FAFAFA')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FAFAFA'), colors.white]),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#2CDBD9')),
    ]))
    
    content.append(items_table)
    content.append(Spacer(1, 30))
    
    # Summary section
    tax_amount = getattr(quotation, 'tax_amount', 0) or 0
    server_charge = 0
    domain_charge = 0
    
    # Get hosting charges
    if hasattr(quotation, 'server_hosting') and quotation.server_hosting:
        if isinstance(quotation.server_hosting, dict):
            if quotation.server_hosting.get('included', False):
                server_charge = quotation.server_hosting.get('unit_price', 0)
    
    if hasattr(quotation, 'domain_registration') and quotation.domain_registration:
        if isinstance(quotation.domain_registration, dict):
            if quotation.domain_registration.get('included', False):
                domain_charge = quotation.domain_registration.get('unit_price', 0)
    
    grand_total = getattr(quotation, 'grand_total', 0) or (subtotal + tax_amount + server_charge + domain_charge)
    
    # Summary table
    summary_data = [
        ['Subtotal:', format_currency(subtotal)],
        ['Tax:', format_currency(tax_amount)],
        ['Server Hosting:', format_currency(server_charge)],
        ['Domain Registration:', format_currency(domain_charge)],
        ['', ''],
        ['Grand Total:', format_currency(grand_total)],
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch], hAlign='RIGHT')
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#2CDBD9')),
        ('LINEBELOW', (0, -2), (-1, -2), 1, colors.black),
    ]))
    
    content.append(summary_table)
    content.append(Spacer(1, 30))
    
    # Terms and conditions
    terms = getattr(quotation, 'terms_conditions', '') or getattr(quotation, 'additional_notes', '')
    if terms:
        content.append(Paragraph("<b>Terms & Conditions:</b>", heading_style))
        # Split terms by newlines and create bullet points
        if isinstance(terms, str):
            terms_list = [term.strip() for term in terms.split('\n') if term.strip()]
            for term in terms_list[:6]:  # Limit to 6 terms
                content.append(Paragraph(f"• {term}", normal_style))
        content.append(Spacer(1, 20))
    
    # Footer
    footer_data = [
        ['Bank Details:', '', 'Contact Information:'],
        ['Account Holder: DOSHI NAMAN PRAKASHBHAI', '', getattr(quotation, 'signatory_name', 'CEO Naman Doshi')],
        ['Account Number: 50100463075872', '', 'hello.digiwave@gmail.com'],
        ['IFSC: HDFC0004227', '', '+91 9624185617'],
        ['Branch: JALARAM MANDIR PALDI', '', ''],
        ['Account Type: SAVING', '', ''],
    ]
    
    footer_table = Table(footer_data, colWidths=[2.5*inch, 0.5*inch, 2.5*inch])
    footer_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
        ('FONTNAME', (2, 1), (2, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    content.append(footer_table)
    
    # Build PDF
    doc.build(content)
    buffer.seek(0)
    
    return buffer