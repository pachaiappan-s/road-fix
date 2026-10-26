import os, uuid, traceback
from functools import wraps
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, session, redirect, send_file
from flask_cors import CORS

from database import db
from models import Ticket, Report
from ai_detector import detect_damage, get_severity
from priority import priority_score, classify_road, STATUS_ORDER
from pdf_generator import generate_work_order_pdf
from email_utils import send_status_email

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'roadfix.db')}"
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-later")
db.init_app(app)
CORS(app)

CONF_THRESHOLD = 0.4
MERGE_RADIUS_M = 20

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


def login_required_page(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper


def login_required_api(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper


def haversine_m(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371000
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


def next_ticket_code():
    n = Ticket.query.count() + 1
    while True:
        code = f"RF-{1000 + n}"
        if not Ticket.query.filter_by(ticket_code=code).first():
            return code
        n += 1


# ---------- Pages ----------
@app.route("/")
def serve_citizen():
    return send_from_directory(FRONTEND_DIR, "citizen.html")


@app.route("/admin")
@login_required_page
def serve_admin():
    return send_from_directory(FRONTEND_DIR, "admin.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return send_from_directory(FRONTEND_DIR, "login.html")
    username = request.form.get("username")
    password = request.form.get("password")
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["logged_in"] = True
        return redirect("/admin")
    return redirect("/login?error=1")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------- Citizen: submit report ----------
@app.route("/api/reports", methods=["POST"])
def submit_report():
    try:
        return submit_report_inner()
    except Exception as e:
        traceback.print_exc()
        db.session.rollback()
        return jsonify({"accepted": False, "message": f"Server error: {e}"}), 500


def submit_report_inner():
    photo = request.files.get("photo")
    lat = float(request.form.get("lat"))
    lng = float(request.form.get("lng"))
    road_name = request.form.get("road_name", "Unknown Road")
    citizen_email = request.form.get("citizen_email") or None

    filename = f"{uuid.uuid4().hex}_{photo.filename}"
    path = os.path.join(UPLOAD_DIR, filename)
    photo.save(path)

    result = detect_damage(path)

    if not result or result["confidence"] < CONF_THRESHOLD:
        db.session.add(Report(photo_path=filename, lat=lat, lng=lng,
                               confidence=(result["confidence"] if result else 0),
                               accepted=False))
        db.session.commit()
        return jsonify({"accepted": False, "message": "No road damage found"}), 200

    severity = get_severity(result["area_pct"])

    candidates = Ticket.query.filter(
        Ticket.status != "Fixed",
        Ticket.damage_type == result["damage_type"]
    ).all()
    match = next((t for t in candidates
                  if haversine_m(lat, lng, t.lat, t.lng) <= MERGE_RADIUS_M), None)

    if match:
        match.report_count += 1
        if severity == "High" or (severity == "Medium" and match.severity == "Low"):
            match.severity = severity
        if citizen_email:
            match.citizen_email = citizen_email
        ticket = match
    else:
        ticket = Ticket(
            ticket_code=next_ticket_code(),
            road_name=road_name, lat=lat, lng=lng,
            damage_type=result["damage_type"], severity=severity,
            ai_confidence=result["confidence"], damage_area_pct=result["area_pct"],
            road_class_score=classify_road(road_name),
            report_count=1, status="Reported",
            photo_path=filename,
            citizen_email=citizen_email,
        )
        db.session.add(ticket)

    db.session.flush()
    db.session.add(Report(ticket_id=ticket.id, photo_path=filename, lat=lat, lng=lng,
                           confidence=result["confidence"], accepted=True))
    db.session.commit()

    return jsonify({"accepted": True, "ticket": ticket.to_dict()}), 201


# ---------- Citizen: lookup ticket ----------
@app.route("/api/lookup/<ticket_code>")
def lookup_ticket(ticket_code):
    t = Ticket.query.filter_by(ticket_code=ticket_code).first()
    if not t:
        return jsonify({"error": "Ticket not found"}), 404
    return jsonify({
        "ticket_code": t.ticket_code,
        "road_name": t.road_name,
        "damage_type": t.damage_type,
        "severity": t.severity,
        "status": t.status,
        "report_count": t.report_count,
    })


# ---------- Admin: list tickets ----------
@app.route("/api/tickets", methods=["GET"])
@login_required_api
def list_tickets():
    status_filter = request.args.get("status", "open")
    severity_filter = request.args.get("severity")

    q = Ticket.query
    if status_filter == "open":
        q = q.filter(Ticket.status != "Fixed")
    if severity_filter:
        q = q.filter(Ticket.severity == severity_filter)

    tickets = q.all()
    result = []
    for t in tickets:
        p = priority_score(t)
        result.append(t.to_dict(priority=p["total"]))
    result.sort(key=lambda x: x["priority"], reverse=True)
    return jsonify(result[:15])


@app.route("/api/tickets/<int:ticket_id>", methods=["GET"])
@login_required_api
def ticket_detail(ticket_id):
    t = Ticket.query.get_or_404(ticket_id)
    p = priority_score(t)
    data = t.to_dict()
    data["priority_breakdown"] = p
    return jsonify(data)


@app.route("/api/tickets/<int:ticket_id>/status", methods=["PATCH"])
@login_required_api
def update_status(ticket_id):
    t = Ticket.query.get_or_404(ticket_id)
    new_status = request.json.get("status")
    if new_status not in STATUS_ORDER:
        return jsonify({"error": "invalid status"}), 400
    t.status = new_status
    if new_status == "Fixed":
        t.fixed_at = datetime.utcnow()
    db.session.commit()

    if t.citizen_email:
        try:
            p = priority_score(t)
            pdf_buffer = generate_work_order_pdf(t, p)
            send_status_email(t.citizen_email, t, pdf_buffer=pdf_buffer)
        except Exception as e:
            print(f"Could not send status email: {e}")

    return jsonify(t.to_dict())


@app.route("/api/tickets/<int:ticket_id>/pdf")
@login_required_api
def ticket_pdf(ticket_id):
    t = Ticket.query.get_or_404(ticket_id)
    p = priority_score(t)
    buffer = generate_work_order_pdf(t, p)
    return send_file(buffer, mimetype="application/pdf",
                      as_attachment=True,
                      download_name=f"{t.ticket_code}_workorder.pdf")


@app.route("/api/stats", methods=["GET"])
@login_required_api
def stats():
    open_tickets = Ticket.query.filter(Ticket.status != "Fixed").count()
    total_tickets = Ticket.query.count()
    accepted_reports = Report.query.filter_by(accepted=True).count()
    rejected_reports = Report.query.filter_by(accepted=False).count()
    total_reports = accepted_reports + rejected_reports

    duplicates_merged = max(0, accepted_reports - total_tickets)
    dup_pct = round((duplicates_merged / accepted_reports) * 100, 0) if accepted_reports else 0
    rej_pct = round((rejected_reports / total_reports) * 100, 0) if total_reports else 0

    fixed = Ticket.query.filter_by(status="Fixed").all()
    if fixed:
        avg_days = sum((t.fixed_at - t.first_reported).total_seconds() for t in fixed) \
                   / len(fixed) / 86400
    else:
        avg_days = 0

    pipeline = {s: Ticket.query.filter_by(status=s).count() for s in STATUS_ORDER}

    return jsonify({
        "open_tickets": open_tickets,
        "duplicates_merged_pct": dup_pct,
        "avg_repair_days": round(avg_days, 1),
        "rejected_pct": rej_pct,
        "pipeline": pipeline,
        "total_tickets": total_tickets,
    })


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)