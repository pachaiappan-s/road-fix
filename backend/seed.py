from datetime import datetime, timedelta
from app import app
from database import db
from models import Ticket
from priority import classify_road

SAMPLE = [
    ("GST Road, Guindy", "Pothole", "High", 14, 19, "Assigned"),
    ("OMR, Perungudi", "Pothole", "High", 11, 12, "Assigned"),
    ("OMR Signal, Sholinganallur", "Pothole", "High", 10, 10, "Verified"),
    ("Tambaram–Mudichur Road", "Pothole", "High", 8, 15, "Verified"),
    ("Usman Road, T. Nagar", "Pothole", "Medium", 12, 27, "Assigned"),
    ("Velachery Main Road", "Alligator crack", "Medium", 9, 23, "Verified"),
    ("Market Road, Koyambedu", "Pothole", "High", 7, 6, "Reported"),
    ("Medavakkam Main Road", "Alligator crack", "Medium", 5, 17, "Reported"),
    ("GST Road, Chromepet", "Pothole", "Medium", 6, 4, "Reported"),
    ("Lattice Bridge Road, Adyar", "Longitudinal crack", "Medium", 4, 14, "Verified"),
    ("2nd Avenue, Anna Nagar", "Pothole", "Medium", 6, 8, "Reported"),
    ("Porur Junction", "Transverse crack", "Low", 5, 9, "Reported"),
    ("Kodambakkam High Road", "Pothole", "Medium", 3, 7, "Reported"),
    ("100 Feet Road, Vadapalani", "Transverse crack", "Low", 2, 3, "Reported"),
    ("5th Street, Adambakkam", "Pothole", "Low", 2, 16, "Reported"),
]

with app.app_context():
    db.create_all()
    for i, (road, dtype, sev, reports, days, status) in enumerate(SAMPLE):
        t = Ticket(
            ticket_code=f"RF-{1041+i}",
            road_name=road,
            lat=13.0 + i*0.01, lng=80.2 + i*0.01,
            damage_type=dtype, severity=sev,
            ai_confidence=0.9, damage_area_pct=5.0 if sev == "High" else 2.0,
            road_class_score=classify_road(road),
            report_count=reports,
            first_reported=datetime.utcnow() - timedelta(days=days),
            status=status,
        )
        db.session.add(t)

    for i in range(20):
        t = Ticket(
            ticket_code=f"RF-{2000+i}",
            road_name="Various", lat=13.0, lng=80.2,
            damage_type="Pothole", severity="Medium",
            ai_confidence=0.85, damage_area_pct=2.5,
            road_class_score=10, report_count=3,
            first_reported=datetime.utcnow() - timedelta(days=30),
            status="Fixed",
            fixed_at=datetime.utcnow() - timedelta(days=20),
        )
        db.session.add(t)

    db.session.commit()
    print("Seeded database.")