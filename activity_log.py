import json

from flask import current_app, has_request_context, request, session

from database import db
from models import ActivityLog


def record_activity(event_type, payload=None, user_id=None):
    """
    Persist a lightweight audit row. Avoid storing symptom answers or chat text (privacy).
    """
    if user_id is None and has_request_context():
        user_id = session.get("user_id")

    ip = None
    if has_request_context() and request.remote_addr:
        ip = str(request.remote_addr)[:45]

    row = ActivityLog(
        user_id=user_id,
        event_type=event_type,
        payload_json=json.dumps(payload) if payload else None,
        ip_address=ip,
    )
    try:
        db.session.add(row)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        if has_request_context():
            current_app.logger.warning("Activity log write failed (%s): %s", event_type, exc)
