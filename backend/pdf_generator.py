from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def generate_work_order_pdf(ticket, priority_breakdown):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "RoadFix - Repair Work Order")

    c.setFont("Helvetica", 11)
    y = height - 100
    lines = [
        f"Ticket: {ticket.ticket_code}",
        f"Location: {ticket.road_name}",
        f"Coordinates: {ticket.lat}, {ticket.lng}",
        f"Damage type: {ticket.damage_type}",
        f"Severity: {ticket.severity}",
        f"AI confidence: {round((ticket.ai_confidence or 0) * 100, 1)}%",
        f"Citizen reports merged: {ticket.report_count}",
        f"First reported: {ticket.first_reported.strftime('%d %b %Y')}",
        f"Current status: {ticket.status}",
        f"Assigned crew: {ticket.crew or 'Unassigned'}",
        "",
        f"Priority score: {priority_breakdown['total']} / 100",
        f"  Severity: {priority_breakdown['severity']}/40",
        f"  Reports merged: {priority_breakdown['reports']}/20",
        f"  Road class: {priority_breakdown['road']}/20",
        f"  Days unresolved: {priority_breakdown['days']}/20",
        "",
        f"Generated: {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}",
    ]
    for line in lines:
        c.drawString(50, y, line)
        y -= 20

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer