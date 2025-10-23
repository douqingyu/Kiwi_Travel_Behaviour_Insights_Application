from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO

def generate_subscription_pdf(subscription):
    """Generate a PDF document for subscription details."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30
    )
    elements.append(Paragraph("Subscription Details", title_style))
    elements.append(Spacer(1, 20))

    # Basic Information
    elements.append(Paragraph("Basic Information", styles['Heading2']))
    basic_data = [
        ["Plan:", subscription.get('plan_name', '-')],
        ["Start Date:", subscription.get('start_date', '-').strftime('%Y-%m-%d %H:%M') if subscription.get('start_date') else '-'],
        ["End Date:", subscription.get('end_date', '-').strftime('%Y-%m-%d %H:%M') if subscription.get('end_date') else '-'],
        ["Type:", 'Free Trial' if subscription.get('is_free_trial') else 'Admin Granted' if subscription.get('granted_by_admin') else 'Paid Subscription']
    ]
    basic_table = Table(basic_data, colWidths=[2*inch, 4*inch])
    basic_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(basic_table)
    elements.append(Spacer(1, 20))

    # Payment Information
    elements.append(Paragraph("Payment Information", styles['Heading2']))
    payment_data = [
        ["Amount:", f"${float(subscription.get('payment_amount', 0)):.2f}" if subscription.get('payment_amount') else '-'],
        ["GST:", f"${float(subscription.get('gst_amount', 0)):.2f}" if subscription.get('gst_amount') else '-'],
        ["Billing Country:", subscription.get('billing_country', '-')],
        ["Created At:",
         subscription.get('created_at', '-').strftime('%Y-%m-%d %H:%M') if subscription.get('created_at') else '-']
    ]
    payment_table = Table(payment_data, colWidths=[2*inch, 4*inch])
    payment_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(payment_table)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue() 