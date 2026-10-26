from datetime import datetime

STATUS_ORDER = ["Reported", "Verified", "Assigned", "Fixed"]

MAJOR_ROADS = ["omr", "gst road", "anna salai", "inner ring road",
               "mount road", "ecr", "tambaram", "velachery"]

def classify_road(road_name):
    name = road_name.lower()
    if any(r in name for r in MAJOR_ROADS):
        return 20
    return 10

def priority_score(ticket):
    sev_score = {"High": 40, "Medium": 25, "Low": 10}.get(ticket.severity, 10)
    reports_score = min(20, round(ticket.report_count * 1.5))
    road_score = ticket.road_class_score
    days = (datetime.utcnow() - ticket.first_reported).days
    days_score = min(20, round(days * 0.8))
    total = sev_score + reports_score + road_score + days_score
    return {
        "severity": sev_score,
        "reports": reports_score,
        "road": road_score,
        "days": days_score,
        "total": min(100, total),
        "days_open": days,
    }