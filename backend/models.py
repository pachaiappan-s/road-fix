from datetime import datetime
from database import db

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_code = db.Column(db.String(20), unique=True)
    road_name = db.Column(db.String(200))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    damage_type = db.Column(db.String(50))
    severity = db.Column(db.String(10))
    ai_confidence = db.Column(db.Float)
    damage_area_pct = db.Column(db.Float)
    road_class_score = db.Column(db.Integer, default=10)
    report_count = db.Column(db.Integer, default=1)
    first_reported = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="Reported")
    crew = db.Column(db.String(50), default="Unassigned")
    fixed_at = db.Column(db.DateTime, nullable=True)
    photo_path = db.Column(db.String(300))
    citizen_email = db.Column(db.String(200), nullable=True)

    def to_dict(self, priority=None):
        d = {
            "id": self.id,
            "ticket_code": self.ticket_code,
            "road_name": self.road_name,
            "lat": self.lat, "lng": self.lng,
            "damage_type": self.damage_type,
            "severity": self.severity,
            "ai_confidence": round((self.ai_confidence or 0) * 100, 1),
            "damage_area_pct": round(self.damage_area_pct or 0, 2),
            "report_count": self.report_count,
            "first_reported": self.first_reported.isoformat(),
            "status": self.status,
            "crew": self.crew,
            "photo_path": self.photo_path,
        }
        if priority:
            d["priority"] = priority
        return d


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("ticket.id"), nullable=True)
    photo_path = db.Column(db.String(300))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    confidence = db.Column(db.Float)
    accepted = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)