"""
HTML-based PDF generator for quotations using WeasyPrint
This provides pixel-perfect rendering matching the HTML template
"""
from io import BytesIO
from datetime import datetime
from django.template.loader import render_to_string
from django.conf import settings
import os

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("WeasyPrint not installed. Install with: pip install weasyprint")


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
        return "RS. 0"
    return f"RS. {amount:,.2f}"


def generate_quotation_html_pdf(quotation):
    """
    Generate PDF from HTML template for quotation
    Returns BytesIO buffer containing the PDF
    """
    if not WEASYPRINT_AVAILABLE:
        raise ImportError("WeasyPrint is required for HTML PDF generation. Install with: pip install weasyprint")
    
    # Prepare data for template
    service_items = quotation.service_items if hasattr(quotation, 'service_items') else []
    if isinstance(service_items, str):
        import json
        service_items = json.loads(service_items)
    
    # Limit to 3 items for single page
    service_items = service_items[:3] if service_items else []
    
    # Calculate totals
    subtotal = sum(item.get('quantity', 0) * item.get('unit_price', 0) for item in service_items)
    tax_amount = getattr(quotation, 'tax_amount', 0) or 0
    server_charge = 0
    domain_charge = 0
    
    if hasattr(quotation, 'server_hosting') and quotation.server_hosting:
        if isinstance(quotation.server_hosting, dict):
            server_charge = quotation.server_hosting.get('unit_price', 0)
        else:
            server_charge = getattr(quotation.server_hosting, 'unit_price', 0)
    
    if hasattr(quotation, 'domain_registration') and quotation.domain_registration:
        if isinstance(quotation.domain_registration, dict):
            domain_charge = quotation.domain_registration.get('unit_price', 0)
        else:
            domain_charge = getattr(quotation.domain_registration, 'unit_price', 0)
    
    grand_total = getattr(quotation, 'grand_total', 0) or (subtotal + tax_amount + server_charge + domain_charge)
    paid = 0
    amount_due = grand_total - paid
    
    # Prepare context
    context = {
        'quotation_no': getattr(quotation, 'quotation_no', 'N/A'),
        'date': format_date(getattr(quotation, 'date', None)),
        'valid_until': format_date(getattr(quotation, 'valid_until', None)),
        'client_name': getattr(quotation, 'client_name', 'N/A'),
        'client_email': getattr(quotation, 'client_email', ''),
        'client_phone': getattr(quotation, 'client_phone', ''),
        'client_address': getattr(quotation, 'client_address', ''),
        'service_items': service_items,
        'subtotal': format_currency(subtotal),
        'tax_amount': format_currency(tax_amount),
        'server_charge': format_currency(server_charge),
        'domain_charge': format_currency(domain_charge),
        'grand_total': format_currency(grand_total),
        'paid': format_currency(paid),
        'amount_due': format_currency(amount_due),
        'notes': getattr(quotation, 'additional_notes', None) or getattr(quotation, 'payment_terms', None) or 'Thank you for your business!',
        'signatory_name': getattr(quotation, 'signatory_name', 'CEO Naman Doshi'),
        'signatory_designation': getattr(quotation, 'signatory_designation', ''),
    }
    
    # Generate HTML
    html_content = generate_quotation_html(context)
    
    # Generate PDF from HTML
    buffer = BytesIO()
    HTML(string=html_content, base_url=settings.BASE_DIR).write_pdf(buffer)
    buffer.seek(0)
    
    return buffer


def generate_quotation_html(context):
    """Generate HTML content for quotation"""
    
    html = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quotation - DIGIWAVE Technologies</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Jaldi:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Jaldi', -apple-system, Roboto, Helvetica, sans-serif;
            background: #fff;
            line-height: 1.5;
        }}
        
        .invoice-container {{
            width: 595px;
            min-height: 842px;
            background: #fff;
            position: relative;
            display: flex;
            flex-direction: column;
        }}
        
        /* Header section */
        .invoice-header {{
            position: relative;
            height: 140px;
        }}
        
        .header-curve {{
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
        }}
        
        .header-content {{
            position: absolute;
            inset: 0;
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gapplay: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .logo-circle {{
            width: 55px;
            height: 55px;
            border-radius: 50%;
            background: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            flex-shrink: 0;
        }}
        
        .logo-circle svg {{
            width: 100%;
            height: 100%;
        }}
        
        .company-name {{
            font-size: 40.422px;
            font-weight: 700;
            color: #fff;
            line-height: 1;
            margin: 0;
        }}
        
        .company-tagline {{
            font-size: 15.307px;
            font-weight: 400;
            color: #fff;
            letter-spacing: 4.133px;
            text-align: center;
        }}
        
        .header-address {{
            position: absolute;
            top: 18px;
            right: 40px;
            text-align: right;
            color: #fff;
            font-size: 10px;
            line-height: 14px;
            max-width: 200px;
        }}
        
        /* Invoice body */
        .invoice-body {{
            padding: 24px 40px;
            flex: 1;
        }}
        
        .invoice-title {{
            font-size: 22px;
            font-weight: 700;
            letter-spacing: 0.44px;
            line-height: 18px;
            text-align: center;
            margin-bottom: 8px;
        }}
        
        .invoice-number {{
            font-size: 14px;
            letter-spacing: 0.28px;
            text-align: center;
            margin-bottom: 24px;
        }}
        
        .invoice-info-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 24px;
        }}
        
        .date-section {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        
        .info-line {{
            display: flex;
            gap: 8px;
            font-size: 14px;
            letter-spacing: 0.28px;
            line-height: 18px;
        }}
        
        .label {{
            font-weight: 700;
        }}
        
        .value {{
            font-weight: 400;
        }}
        
        .recipient-section {{
            text-align: right;
            max-width: 177px;
            font-size: 12px;
            line-height: 18px;
        }}
        
        .divider {{
            border-top: 1px solid #000;
            margin-bottom: 24px;
        }}
        
        /* Table */
        .invoice-table {{
            width: 515px;
            border-collapse: collapse;
            margin: 24px 0;
        }}
        
        .table-header {{
            background: #F3FFFF;
            border-bottom: 2px solid #2CDBD9;
        }}
        
        .table-header th {{
            padding: 8px 11px;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.28px;
            line-height: 18px;
            text-align: center;
        }}
        
        .table-header th:first-child {{
            text-align: left;
            width: 206px;
        }}
        
        .table-row {{
            background: #FAFAFA;
        }}
        
        .table-row td {{
            padding: 8px 11px;
            font-size: 14px;
            letter-spacing: 0.28px;
            line-height: 18px;
            text-align: center;
        }}
        
        .table-row td:first-child {{
            text-align: left;
        }}
        
        /* Bottom section */
        .bottom-section {{
            display: flex;
            justify-content: space-between;
            margin: 32px 0;
        }}
        
        .notes-section {{
            flex: 1;
            max-width: 198px;
        }}
        
        .notes-section .label {{
            font-size: 14px;
            letter-spacing: 0.28px;
            line-height: 18px;
            margin-bottom: 8px;
            display: block;
        }}
        
        .notes-text {{
            font-size: 12px;
            letter-spacing: 0.24px;
            line-height: 18px;
        }}
        
        .summary-section {{
            display: flex;
            flex-direction: column;
            gap: 10px;
            min-width: 243px;
        }}
        
        .summary-line {{
            display: flex;
            justify-content: space-between;
            font-size: 14px;
            letter-spacing: 0.28px;
            line-height: 18px;
        }}
        
        .summary-line .label {{
            width: 89px;
        }}
        
        .summary-line .value {{
            width: 102px;
            text-align: right;
        }}
        
        .total-line {{
            color: #2CDBD9;
            font-weight: 700;
        }}
        
        /* Amount due box */
        .amount-due-box {{
            display: flex;
            justify-content: flex-end;
            margin-bottom: 32px;
        }}
        
        .amount-due-label,
        .amount-due-value {{
            background: #052455;
            color: #fff;
            padding: 5px 13px;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.28px;
            line-height: 18px;
        }}
        
        .amount-due-value {{
            text-align: right;
            padding-left: 106px;
        }}
        
        /* Footer info */
        .footer-info {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding-top: 24px;
            padding-bottom: 20px;
            border-top: 1px solid #e5e7eb;
        }}
        
        .bank-details {{
            font-size: 12px;
            letter-spacing: 0.24px;
            line-height: 18px;
            flex: 1;
        }}
        
        .contact-info {{
            text-align: right;
            font-size: 12px;
            letter-spacing: 0.24px;
            line-height: 18px;
            flex: 1;
        }}
        
        .contact-name {{
            font-weight: 700;
            margin-bottom: 4px;
        }}
        
        .qr-section {{
            display: flex;
            justify-content: center;
            align-items: flex-start;
            padding: 0 20px;
        }}
        
        .qr-code {{
            width: 40px;
            height: 40px;
            background: #f0f0f0;
            border: 1px solid #ddd;
        }}
        
        /* Bottom bar */
        .bottom-bar {{
            width: 100%;
            height: 9px;
            background: #052455;
            margin-top: auto;
        }}
    </style>
</head>
<body>
    <div class="invoice-container">
        <!-- Header with curved background -->
        <div class="invoice-header">
            <svg class="header-curve" viewBox="0 0 595 140" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
                <path d="M0 0H595V103L298 140L0 103V0Z" fill="#052455"/>
            </svg>
            <div class="header-content">
                <div class="header-left">
                    <div class="logo-circle">
                        <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="50" cy="50" r="45" fill="#052455"/>
                            <text x="50" y="55" font-family="Arial, sans-serif" font-size="24" font-weight="bold" fill="white" text-anchor="middle">DW</text>
                        </svg>
                    </div>
                    <div>
                        <h1 class="company-name">DIGIWAVE</h1>
                        <p class="company-tagline">TECHNOLOGIES</p>
                    </div>
                </div>
                <div class="header-address">
                    401 medani jain hostel, navjivan press road, income tax cross road, Ahmedabad, gujarat, india-380009
                </div>
            </div>
        </div>

        <!-- Invoice body -->
        <div class="invoice-body">
            <!-- Invoice title and number -->
            <h2 class="invoice-title">Quotation</h2>
            <p class="invoice-number">#{context['quotation_no']}</p>

            <!-- Date and recipient info -->
            <div class="invoice-info-row">
                <div class="date-section">
                    <div class="info-line">
                        <span class="label">Date:</span>
                        <span class="value">{context['date']}</span>
                    </div>
                    <div class="info-line">
                        <span class="label">Due Date:</span>
                        <span class="value">{context['valid_until']}</span>
                    </div>
                </div>
                <div class="recipient-section">
                    <p class="label">To:</p>
                    <p>{context['client_name']}</p>
                    {f"<p>{context['client_email']}</p>" if context['client_email'] else ""}
                    {f"<p>{context['client_phone']}</p>" if context['client_phone'] else ""}
                    {f"<p>{context['client_address']}</p>" if context['client_address'] else ""}
                </div>
            </div>

            <!-- Divider line -->
            <div class="divider"></div>

            <!-- Items table -->
            <table class="invoice-table">
                <thead>
                    <tr class="table-header">
                        <th>Name</th>
                        <th>Quantity</th>
                        <th>Price</th>
                        <th>Discount</th>
                        <th>Tax</th>
                        <th>Linetotal</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join([f'''
                    <tr class="table-row">
                        <td>{item.get('description', item.get('category', 'N/A'))}</td>
                        <td>{item.get('quantity', 0)}</td>
                        <td>{item.get('unit_price', 0)}</td>
                        <td>-</td>
                        <td>-</td>
                        <td>{item.get('quantity', 0) * item.get('unit_price', 0)}</td>
                    </tr>
                    ''' for item in context['service_items']])}
                </tbody>
            </table>

            <!-- Notes and summary section -->
            <div class="bottom-section">
                <div class="notes-section">
                    <span class="label">Note:</span>
                    <p class="notes-text">{context['notes']}</p>
                </div>
                <div class="summary-section">
                    <div class="summary-line">
                        <span class="label">Subtotal:</span>
                        <span class="value">{context['subtotal']}</span>
                    </div>
                    <div class="summary-line">
                        <span class="label">Tax:</span>
                        <span class="value">{context['tax_amount']}</span>
                    </div>
                    <div class="summary-line">
                        <span class="label">Server charge:</span>
                        <span class="value">{context['server_charge']}</span>
                    </div>
                    <div class="summary-line">
                        <span class="label">Domain charge:</span>
                        <span class="value">{context['domain_charge']}</span>
                    </div>
                    <div class="summary-line total-line">
                        <span class="label">Total:</span>
                        <span class="value">{context['grand_total']}</span>
                    </div>
                    <div class="summary-line">
                        <span class="label">Paid:</span>
                        <span class="value">{context['paid']}</span>
                    </div>
                </div>
            </div>

            <!-- Amount due box -->
            <div class="amount-due-box">
                <div class="amount-due-label">Amount Due</div>
                <div class="amount-due-value">{context['amount_due']}</div>
            </div>

            <!-- Footer info -->
            <div class="footer-info">
                <div class="bank-details">
                    <p><strong>Bank Details:</strong></p>
                    <p>Account Holder: DOSHI NAMAN PRAKASHBHAI</p>
                    <p>Account Number: 50100463075872</p>
                    <p>IFSC: HDFC0004227</p>
                    <p>Branch: JALARAM MANDIR PALDI</p>
                    <p>Account Type: SAVING</p>
                </div>
                <div class="qr-section">
                    <svg class="qr-code" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
                        <rect width="40" height="40" fill="white"/>
                        <rect x="5" y="5" width="10" height="10" fill="#052455"/>
                        <rect x="25" y="5" width="10" height="10" fill="#052455"/>
                        <rect x="5" y="25" width="10" height="10" fill="#052455"/>
                        <rect x="20" y="20" width="5" height="5" fill="#052455"/>
                    </svg>
                </div>
                <div class="contact-info">
                    <p class="contact-name">{context['signatory_name']}</p>
                    <p>hello.digiwave@gmail.com</p>
                    <p>+91 9624185617</p>
                </div>
            </div>
        </div>

        <!-- Bottom bar -->
        <div class="bottom-bar"></div>
    </div>
</body>
</html>
    '''
    
    return html
