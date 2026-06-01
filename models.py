from datetime import datetime, timezone

from database import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    activity_entries = db.relationship("ActivityLog", backref="user", lazy=True)
    insight_snapshots = db.relationship("InsightSnapshot", backref="user", lazy=True)


class InsightSnapshot(db.Model):
    """
    Stored category scores after a symptom check (logged-in users only).
    Individual symptom answers are not persisted—only educational aggregates.
    """

    __tablename__ = "insight_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    hormonal = db.Column(db.Float, nullable=False)
    metabolic = db.Column(db.Float, nullable=False)
    inflammatory = db.Column(db.Float, nullable=False)
    dominant_label = db.Column(db.String(80), nullable=False)
    # "baseline" = full symptom checker; "retake" = shorter follow-up questionnaire
    test_type = db.Column(db.String(16), nullable=False, default="baseline")


class ActivityLog(db.Model):
    __tablename__ = "activity_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    payload_json = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
