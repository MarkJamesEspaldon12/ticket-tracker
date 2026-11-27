import os

from flask import Flask, Response, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

db = SQLAlchemy()

REQUESTS = Counter(
    "http_requests", "HTTP requests handled", ["method", "path", "status"]
)


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="open")

    def to_dict(self):
        return {"id": self.id, "title": self.title, "status": self.status}


def create_app(db_url=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url or os.environ.get(
        "DATABASE_URL", "sqlite:////tmp/tickets.db"
    )
    db.init_app(app)
    with app.app_context():
        db.create_all()

    @app.after_request
    def count_request(response):
        # Use the route pattern (/tickets/<int:ticket_id>/close), not the
        # real path, so every ticket id doesn't become a new metric series.
        path = request.url_rule.rule if request.url_rule else "unmatched"
        REQUESTS.labels(request.method, path, str(response.status_code)).inc()
        return response

    @app.get("/health")
    def health():
        try:
            db.session.execute(db.text("SELECT 1"))
        except Exception:
            return {"status": "db down"}, 503
        return {"status": "ok"}

    @app.get("/tickets")
    def list_tickets():
        tickets = Ticket.query.order_by(Ticket.id).all()
        return jsonify([t.to_dict() for t in tickets])

    @app.post("/tickets")
    def create_ticket():
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()
        if not title:
            return {"error": "title is required"}, 400
        ticket = Ticket(title=title)
        db.session.add(ticket)
        db.session.commit()
        return ticket.to_dict(), 201

    @app.patch("/tickets/<int:ticket_id>/close")
    def close_ticket(ticket_id):
        ticket = db.session.get(Ticket, ticket_id)
        if ticket is None:
            return {"error": "ticket not found"}, 404
        ticket.status = "closed"
        db.session.commit()
        return ticket.to_dict()

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)

    return app
