from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
from datetime import datetime


def generate_quotation_pdf(quotation):
    """Generate PDF for quotation"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0, bottomMargin=10*mm)
    
    # Container for elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading1'],
        fontSize=40,
        textColor=colors.white,
        alignment=TA_LEFT,
        spaceAfter=0,
    )
    
    subheader_style = ParagraphStyle(
        'CustomSubHeader',
        parent=styles['Normal'],
        fontSize=15,
        textColor=colors.white,
        alignment=TA_LEFT,
        letterSpacing=4,
    )
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=22,
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    
    # Header with blue background
    header_data = [
        [
            Paragraph('<b>DIGIWAVE</b>', header_style),
            Paragraph('401 medani jain hostel, navjivan press road,<br/>Ahmedabad, Gujarat, India-380009', 
                     ParagraphStyle('HeaderAddress', parent=styles['Normal'], fontSize=10, textColor=colors.white, alignment=TA_RIGHT))
        ],
        [
            Paragraph('TECHNOLOGIES', subheader_style),
            ''
        ]
    ]
    
    header_table = Table(header_data, colWidths=[200, 300])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#052455')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('TOPPADDING', (0, 0), (-1, -1), 20),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 20))
    
    # Title
    elements.append(Paragraph('<b>Quotation</b>', title_style))
    elements.append(Spacer(1, 10))
    
    # Quotation details
    details_data = [
        ['Date:', quotation.date.strftime('%d %B, %Y') if quotation.date else 'N/A', 
         'Quotation No:', quotation.quotation_no],
        ['Due Date:', quotation.valid_until.strftime('%d %B, %Y') if quotation.valid_until else 'N/A',
         'To:', quotation.client_name or 'N/A'],
    ]
    
    details_table = Table(details_data, colWidths=[60, 150, 80, 200])
    details_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 20))
    
    # Client address
    if quotation.client_address:
        client_info = Paragraph(f'<b>Client Address:</b><br/>{quotation.client_address}', 
                               ParagraphStyle('ClientInfo', parent=styles['Normal'], fontSize=10))
        elements.append(client_info)
        elements.append(Spacer(1, 20))
    
    # Service items table
    service_data = [['Name', 'Quantity', 'Price', 'Discount', 'Tax', 'Line Total']]
    
    for item in quotation.service_items:
        service_data.append([
            item.get('description', item.get('category', '')),
            str(item.get('quantity', 0)),
            f"₹{item.get('unit_price', 0):,.2f}",
            '-',
            '-',
            f"₹{item.get('quantity', 0) * item.get('unit_price', 0):,.2f}"
        ])
    
    service_table = Table(service_data, colWidths=[150, 60, 70, 60, 50, 100])
    service_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3FFFF')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FAFAFA')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#2CDBD9')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(service_table)
    elements.append(Spacer(1, 20))
    
    # Summary
    summary_data = [
        ['Subtotal:', f"₹{quotation.subtotal or 0:,.2f}"],
        ['Tax:', f"₹{quotation.tax_amount or 0:,.2f}"],
        ['Server charge:', f"₹{quotation.server_hosting.get('unit_price', 0) if quotation.server_hosting else 0:,.2f}"],
        ['Domain charge:', f"₹{quotation.domain_registration.get('unit_price', 0) if quotation.domain_registration else 0:,.2f}"],
        ['Total:', f"₹{quotation.grand_total or 0:,.2f}"],
        ['Paid:', '₹0.00'],
    ]
    
    summary_table = Table(summary_data, colWidths=[150, 100])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 4), (-1, 4), colors.HexColor('#2CDBD9')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Notes
    if quotation.additional_notes or quotation.payment_terms:
        notes = Paragraph(f'<b>Note:</b><br/>{quotation.additional_notes or quotation.payment_terms}',
                         ParagraphStyle('Notes', parent=styles['Normal'], fontSize=10))
        elements.append(notes)
        elements.append(Spacer(1, 20))
    
    # Amount Due
    amount_due_data = [[
        Paragraph('<b>Amount Due</b>', ParagraphStyle('AmountDue', parent=styles['Normal'], 
                 fontSize=12, textColor=colors.white, alignment=TA_CENTER)),
        Paragraph(f'<b>₹{quotation.grand_total or 0:,.2f}</b>', ParagraphStyle('AmountValue', 
                 parent=styles['Normal'], fontSize=12, textColor=colors.white, alignment=TA_RIGHT))
    ]]
    
    amount_table = Table(amount_due_data, colWidths=[150, 200])
    amount_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#052455')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(amount_table)
    elements.append(Spacer(1, 20))
    
    # Bank details
    bank_details = Paragraph(
        '<b>Bank Details:</b><br/>'
        'Account Holder: DOSHI NAMAN PRAKASHBHAI<br/>'
        'Account Number: 50100463075872<br/>'
        'IFSC: HDFC0004227<br/>'
        'Branch: JALARAM MANDIR PALDI<br/>'
        'Account Type: SAVING',
        ParagraphStyle('BankDetails', parent=styles['Normal'], fontSize=9)
    )
    elements.append(bank_details)
    elements.append(Spacer(1, 20))
    
    # Signature
    signature = Paragraph(
        f'<b>{quotation.signatory_name or "CEO Naman Doshi"}</b><br/>'
        'hello.digiwave@gmail.com<br/>'
        '+91 9624185617',
        ParagraphStyle('Signature', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT)
    )
    elements.append(signature)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer
