import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from reportlab.lib import colors

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from database import get_db

router = APIRouter(
    prefix="/reports",
    tags=["Executive Reports & PDF/CSV Exports"]
)


@router.get(
    "/export/vendors-csv",
    summary="Export Platform Vendors CSV Report",
    description="Generates a downloadable CSV report containing all vendor accounts (ID, Name, Email, Status, Orders, Units Sold, Total Revenue in ₹ INR).",
    response_description="CSV spreadsheet file attachment response ('shopsense_vendor_report.csv')"
)
def export_vendors_csv_report(db: Session = Depends(get_db)):
    vendors = db.query(models.Vendor).filter(models.Vendor.role == "vendor").all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Vendor ID",
        "Vendor Name",
        "Email Address",
        "Account Status",
        "Total Orders",
        "Total Units Sold",
        "Total Revenue (INR)"
    ])

    for v in vendors:
        v_stats = (
            db.query(
                func.coalesce(func.sum(models.Transaction.total_amount), 0.0).label("revenue"),
                func.coalesce(func.count(models.Transaction.id), 0).label("orders"),
                func.coalesce(func.sum(models.Transaction.quantity), 0).label("units_sold")
            )
            .join(models.Product, models.Transaction.product_id == models.Product.id)
            .filter(models.Product.vendor_id == v.id)
            .first()
        )

        v_rev = round(float(v_stats.revenue), 2) if v_stats and v_stats.revenue else 0.0
        v_orders = int(v_stats.orders) if v_stats and v_stats.orders else 0
        v_units = int(v_stats.units_sold) if v_stats and v_stats.units_sold else 0
        status_str = "REJECTED" if v.status == "suspended" else v.status.upper()

        writer.writerow([
            v.id,
            v.name,
            v.email,
            status_str,
            v_orders,
            v_units,
            f"{v_rev:.2f}"
        ])

    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=shopsense_vendor_report.csv"
        }
    )


@router.get(
    "/export/vendors-pdf",
    summary="Export Executive Platform Performance PDF Report",
    description="Generates a formatted executive PDF report containing a header title, generation timestamp, platform executive KPI summary (Total Revenue in ₹ INR, Active Merchants, Total Orders), and a clean vendor financial performance directory table.",
    response_description="PDF document file attachment response ('shopsense_platform_report.pdf')"
)
def export_vendors_pdf_report(db: Session = Depends(get_db)):
    vendors = db.query(models.Vendor).filter(models.Vendor.role == "vendor").all()

    total_platform_revenue = db.query(func.sum(models.Transaction.total_amount)).scalar() or 0.0
    active_vendors_count = db.query(models.Vendor).filter(models.Vendor.role == "vendor", models.Vendor.status == "active").count()
    total_orders_count = db.query(models.Transaction).count()

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        fontName="Helvetica-Bold",
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        fontName="Helvetica",
        spaceAfter=14
    )

    section_heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        fontName="Helvetica-Bold",
        spaceAfter=8,
        spaceBefore=12
    )

    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
        fontName="Helvetica"
    )

    cell_bold_style = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
        fontName="Helvetica-Bold"
    )

    cell_header_style = ParagraphStyle(
        'TableHeaderCell',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        textColor=colors.white,
        fontName="Helvetica-Bold"
    )

    story = []

    generation_time = datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC")
    story.append(Paragraph("ShopSense — Platform Performance Report", title_style))
    story.append(Paragraph(f"Generated on {generation_time} | Platform Administration", subtitle_style))

    summary_data = [
        [
            Paragraph("Total Platform Revenue (INR)", cell_bold_style),
            Paragraph("Active Vendors", cell_bold_style),
            Paragraph("Total Platform Orders", cell_bold_style)
        ],
        [
            Paragraph(f"<b>Rs. {total_platform_revenue:,.2f}</b>", cell_style),
            Paragraph(f"<b>{active_vendors_count} merchants</b>", cell_style),
            Paragraph(f"<b>{total_orders_count} orders</b>", cell_style)
        ]
    ]

    summary_table = Table(summary_data, colWidths=[180, 180, 180])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BORDER', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Vendor Directory & Financial Performance Breakdown", section_heading_style))

    table_data = [
        [
            Paragraph("ID", cell_header_style),
            Paragraph("Vendor Name", cell_header_style),
            Paragraph("Email Address", cell_header_style),
            Paragraph("Status", cell_header_style),
            Paragraph("Orders", cell_header_style),
            Paragraph("Units Sold", cell_header_style),
            Paragraph("Total Revenue (INR)", cell_header_style)
        ]
    ]

    for v in vendors:
        v_stats = (
            db.query(
                func.coalesce(func.sum(models.Transaction.total_amount), 0.0).label("revenue"),
                func.coalesce(func.count(models.Transaction.id), 0).label("orders"),
                func.coalesce(func.sum(models.Transaction.quantity), 0).label("units_sold")
            )
            .join(models.Product, models.Transaction.product_id == models.Product.id)
            .filter(models.Product.vendor_id == v.id)
            .first()
        )

        v_rev = round(float(v_stats.revenue), 2) if v_stats and v_stats.revenue else 0.0
        v_orders = int(v_stats.orders) if v_stats and v_stats.orders else 0
        v_units = int(v_stats.units_sold) if v_stats and v_stats.units_sold else 0
        status_str = "REJECTED" if v.status == "suspended" else v.status.upper()

        table_data.append([
            Paragraph(f"#{v.id}", cell_style),
            Paragraph(v.name, cell_bold_style),
            Paragraph(v.email, cell_style),
            Paragraph(status_str, cell_style),
            Paragraph(str(v_orders), cell_style),
            Paragraph(str(v_units), cell_style),
            Paragraph(f"Rs. {v_rev:,.2f}", cell_bold_style)
        ])

    pdf_table = Table(table_data, colWidths=[35, 115, 140, 65, 50, 55, 80])
    pdf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))

    story.append(pdf_table)

    doc.build(story)
    pdf_bytes = pdf_buffer.getvalue()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=shopsense_platform_report.pdf"
        }
    )
