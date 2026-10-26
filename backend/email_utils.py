import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


def send_status_email(to_email, ticket, pdf_buffer=None):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD or not to_email:
        print("Email skipped: missing credentials or recipient email")
        return False

    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = f"RoadFix update - {ticket.ticket_code} is now {ticket.status}"

    body = f"""Hello,

Your road damage report ({ticket.ticket_code}) at {ticket.road_name} has been updated.

New status: {ticket.status}
Damage type: {ticket.damage_type}
Severity: {ticket.severity}

Thank you for helping improve our roads.

- RoadFix Team
"""
    msg.attach(MIMEText(body, "plain"))

    if pdf_buffer:
        part = MIMEApplication(pdf_buffer.read(), Name=f"{ticket.ticket_code}_workorder.pdf")
        part["Content-Disposition"] = f'attachment; filename="{ticket.ticket_code}_workorder.pdf"'
        msg.attach(part)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False