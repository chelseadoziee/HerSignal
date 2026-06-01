"""
HerSignal Flask application.

For the shareable demo on Streamlit Cloud, set the main file to streamlit_app.py
(not this file). If Cloud runs this file via `streamlit run app.py`, we delegate
to streamlit_app.py automatically.
"""
from pathlib import Path
import os
import sys

_ROOT = Path(__file__).resolve().parent


def _streamlit_is_running_this_file():
    if os.getenv("STREAMLIT_RUNTIME_ENVIRONMENT"):
        return True
    cmd = " ".join(sys.argv).lower()
    return "streamlit" in cmd and "run" in cmd


if _streamlit_is_running_this_file() and (_ROOT / "streamlit_app.py").is_file():
    os.chdir(_ROOT)
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    import runpy

    runpy.run_path(str(_ROOT / "streamlit_app.py"), run_name="__main__")
    raise SystemExit(0)

from functools import wraps
import logging
import secrets
import threading
import time
from datetime import datetime, timedelta
from io import BytesIO

from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for
from textwrap import wrap

from activity_log import record_activity
from blueprints.auth import auth_bp
from chatbot.responses import get_faq_response
from chatbot.matcher import warmup_faq_matcher
from logic.schema_migrations import ensure_insight_snapshot_test_type
from logic.scoring_engine import (
    load_symptom_questions,
    normalise_response,
    calculate_category_scores,
)
from logic.score_normalization import (
    max_possible_category_scores,
    normalize_scores_unit_interval,
    normalized_deltas,
    test_type_is_retake,
)
from logic.follow_up_narrative import (
    build_category_trends,
    build_category_interpretation_sentences,
    build_overall_pattern_summary,
    dominant_pattern_note,
    followup_reflection_bullets,
)
from logic.result_generator import generate_result_data
from logic.insight_snapshots import (
    dominant_category_label,
    format_delta,
    snapshots_with_deltas,
    snapshot_select_options,
    sparkline_specs,
)
from dashboard.chart_builder import build_symptom_chart

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from database import db
from models import ActivityLog, InsightSnapshot, User  # noqa: F401 -- register models with SQLAlchemy

_instance_dir = _ROOT / "instance"


def _default_database_uri():
    explicit = os.getenv("DATABASE_URL", "").strip()
    if explicit:
        return explicit
    try:
        _instance_dir.mkdir(parents=True, exist_ok=True)
        db_file = _instance_dir / "hersignal.sqlite"
        return "sqlite:///" + str(db_file.resolve())
    except OSError:
        return "sqlite:////tmp/hersignal.sqlite"


def _init_database():
    """Create tables when the database is writable (skip hard failure on read-only hosts)."""
    try:
        _instance_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    try:
        with app.app_context():
            db.create_all()
            ensure_insight_snapshot_test_type(db)
    except Exception as error:
        app.logger.exception(
            "Database init failed; login and insights may be unavailable until "
            "DATABASE_URL points to a writable store: %s",
            error,
        )


def _load_secret_key():
    """Stable session signing key across restarts (stored in instance/.secret_key)."""
    env_key = os.getenv("SECRET_KEY")
    if env_key:
        return env_key
    key_path = _instance_dir / ".secret_key"
    if key_path.is_file():
        return key_path.read_text(encoding="utf-8").strip()
    key = secrets.token_hex(32)
    key_path.write_text(key, encoding="utf-8")
    return key


app = Flask(__name__)
app.secret_key = _load_secret_key()
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "false").strip().lower() == "true"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=14)
app.config["SQLALCHEMY_DATABASE_URI"] = _default_database_uri()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
app.register_blueprint(auth_bp)

_init_database()

MAX_CHAT_MESSAGE_LENGTH = 500
ASK_RATE_LIMIT_COUNT = 12
ASK_RATE_LIMIT_WINDOW_SECONDS = 60

logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)
if not os.getenv("SECRET_KEY"):
    app.logger.info("Using session secret from instance/.secret_key (set SECRET_KEY in production).")


def _warmup_faq_in_background():
    def _run():
        with app.app_context():
            try:
                warmup_faq_matcher()
            except Exception:
                app.logger.exception("Background FAQ warmup failed")

    threading.Thread(target=_run, daemon=True, name="faq-warmup").start()


_warmup_faq_in_background()

RETAKE_QUESTIONS_PATH = Path(__file__).resolve().parent / "data" / "retake_questions.json"


def _questions_for_normalizing_snapshot(snapshot, baseline_questions, retake_questions):
    """Choose the question list that matches how the stored raw scores were produced."""
    tt = getattr(snapshot, "test_type", None) or "baseline"
    if test_type_is_retake(tt):
        return retake_questions
    return baseline_questions


def _latest_insight_for_user(user_id):
    return (
        InsightSnapshot.query.filter_by(user_id=user_id)
        .order_by(InsightSnapshot.created_at.desc())
        .first()
    )


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)

    return wrapped_view


@app.context_processor
def inject_insight_count():
    base = {
        "static_version": "6",
        "max_chat_message_length": MAX_CHAT_MESSAGE_LENGTH,
        "is_logged_in": bool(session.get("user_id")),
        "page_title": "HerSignal",
        "hero_title": "HerSignal",
        "hero_subtitle": None,
        "hero_variant": "compact",
        "hero_id": "page-hero-title",
        "show_hero": True,
        "show_journey": False,
        "show_disclaimer": True,
        "active_step": None,
    }
    if not session.get("user_id"):
        return {**base, "insight_count": 0}
    try:
        n = InsightSnapshot.query.filter_by(user_id=session["user_id"]).count()
    except Exception:
        n = 0
    return {**base, "insight_count": n}


def _layout(chat=False, checker=False, results=False, insights=False, **kwargs):
    """Default template layout variables for pages."""
    active_step = None
    if chat:
        active_step = "chat"
    elif checker:
        active_step = "checker"
    elif results:
        active_step = "results"
    elif insights:
        active_step = "insights"
    defaults = {
        "hero_variant": "compact",
        "show_hero": True,
        "show_journey": active_step is not None,
        "show_disclaimer": True,
        "active_step": active_step,
    }
    defaults.update(kwargs)
    return defaults


def _symptom_layout(**kwargs):
    return _layout(
        checker=True,
        page_title="Symptom checker — HerSignal",
        hero_title="Symptom insight checker",
        hero_subtitle="Answer yes, no, or maybe—HerSignal maps responses into hormonal, metabolic, and inflammatory patterns.",
        hero_id="symptom-page-title",
        **kwargs,
    )


def _results_layout(**kwargs):
    return _layout(
        results=True,
        page_title="Your results — HerSignal",
        hero_title="Your pattern summary",
        hero_subtitle="Educational category scores from your latest check—not a diagnosis.",
        hero_id="results-hero-title",
        **kwargs,
    )


def _insights_layout(**kwargs):
    return _layout(
        insights=True,
        page_title="My insights — HerSignal",
        hero_title="My insights",
        hero_subtitle="Private timeline of your category scores across checks.",
        hero_id="insights-hero-title",
        **kwargs,
    )


def _retake_layout(**kwargs):
    return _layout(
        insights=True,
        page_title="Follow-up check — HerSignal",
        hero_title="Follow-up insight check",
        hero_subtitle="A shorter check compared with your most recent saved insight.",
        hero_id="retake-page-title",
        **kwargs,
    )


@app.route("/health")
def health():
    """Fast check that the web server is up (does not load the FAQ model)."""
    return jsonify({"status": "ok"}), 200


def draw_wrapped_text(pdf, text, x, y, max_chars=95, line_height=16):
    """
    Draw wrapped text onto the PDF and return the new y position.
    """
    if not text:
        return y

    wrapped_lines = []
    for paragraph in str(text).split("\n"):
        if paragraph.strip() == "":
            wrapped_lines.append("")
        else:
            wrapped_lines.extend(wrap(paragraph, width=max_chars))

    for line in wrapped_lines:
        pdf.drawString(x, y, line)
        y -= line_height

    return y


def _is_ask_rate_limited():
    """
    Apply lightweight per-session rate limiting for chatbot submissions.
    """
    now = time.time()
    timestamps = session.get("ask_timestamps", [])
    valid_timestamps = [
        float(ts) for ts in timestamps
        if now - float(ts) <= ASK_RATE_LIMIT_WINDOW_SECONDS
    ]

    if len(valid_timestamps) >= ASK_RATE_LIMIT_COUNT:
        session["ask_timestamps"] = valid_timestamps
        return True

    valid_timestamps.append(now)
    session["ask_timestamps"] = valid_timestamps
    return False


@app.route("/")
def home():
    """
    Render the landing page.
    If the user has not given a name yet, show the welcome/name form first.
    """
    try:
        user_name = session.get("user_name", "")
        return render_template(
            "index.html",
            faq_response=None,
            faq_error=None,
            user_name=user_name,
            user_message=None,
            **_layout(
                chat=True,
                page_title="HerSignal",
                hero_variant="landing",
                hero_title="HerSignal",
                hero_subtitle="Explore PCOS questions and symptom patterns with clear, structured educational support.",
                hero_id="site-title",
            ),
        )
    except Exception as error:
        app.logger.exception("Error loading home page: %s", error)
        return render_template(
            "index.html",
            faq_response="HerSignal could not load the page properly just now. Please refresh and try again.",
            faq_error="Something went wrong while loading the page.",
            user_name=None,
            user_message=None,
            **_layout(chat=True, hero_variant="landing", hero_id="site-title"),
        ), 500


@app.route("/set_name", methods=["POST"])
def set_name():
    """
    Store the user's name and return them to the landing page.
    """
    try:
        user_name = request.form.get("user_name", "").strip()

        if not user_name:
            return render_template(
                "index.html",
                faq_response=None,
                faq_error="Please enter your name before continuing.",
                user_name=None,
                user_message=None,
                **_layout(chat=True, hero_variant="landing", hero_id="site-title"),
            )

        session["user_name"] = user_name
        record_activity("guest_name_set", {"name_length": len(user_name)})
        return redirect(url_for("home"))

    except Exception as error:
        app.logger.exception("Error setting user name: %s", error)
        return render_template(
            "index.html",
            faq_response=None,
            faq_error="HerSignal could not save your name just now. Please try again.",
            user_name=None,
            user_message=None,
            **_layout(chat=True, hero_variant="landing", hero_id="site-title"),
        ), 500


def _ask_wants_json() -> bool:
    return (
        request.accept_mimetypes.best_match(
            ["application/json", "text/html"], "text/html"
        )
        == "application/json"
    )


def _ask_render(user_name, faq_response, faq_error, user_message, status=200):
    payload = {
        "faq_response": faq_response,
        "faq_error": faq_error,
        "user_message": user_message,
    }
    if _ask_wants_json():
        return jsonify(payload), status
    return (
        render_template(
            "index.html",
            user_name=user_name,
            **payload,
            **_layout(
                chat=True,
                page_title="HerSignal",
                hero_variant="landing",
                hero_title="HerSignal",
                hero_subtitle="Explore PCOS questions and symptom patterns with clear, structured educational support.",
                hero_id="site-title",
            ),
        ),
        status,
    )


@app.route("/ask", methods=["POST"])
def ask():
    """
    Handle FAQ chatbot questions from the landing page.
    Supports full-page form posts and JSON responses (Accept: application/json).
    """
    user_name = session.get("user_name", "").strip()

    try:
        if _is_ask_rate_limited():
            return _ask_render(
                user_name,
                faq_response=(
                    "HerSignal has received many questions in a short time. "
                    "Please wait a moment and try again."
                ),
                faq_error="Please slow down and try again in about a minute.",
                user_message=request.form.get("user_message", "").strip(),
                status=429,
            )

        user_message = request.form.get("user_message", "").strip()

        if not user_message:
            if user_name:
                faq_response = f"I’m here to help, {user_name}. Please type a short PCOS-related question."
            else:
                faq_response = "I’m here to help. Please type a short PCOS-related question."

            return _ask_render(
                user_name,
                faq_response=faq_response,
                faq_error="Please enter a question before submitting.",
                user_message=user_message,
            )

        if len(user_message) > MAX_CHAT_MESSAGE_LENGTH:
            return _ask_render(
                user_name,
                faq_response=(
                    "HerSignal works best with short questions. "
                    "Please shorten your message and try again."
                ),
                faq_error=f"Please keep your question under {MAX_CHAT_MESSAGE_LENGTH} characters.",
                user_message=user_message,
            )

        faq_response = get_faq_response(user_message)

        if not faq_response or not str(faq_response).strip():
            faq_response = (
                "HerSignal could not find a strong match for that question just now. "
                "Try asking in a shorter and more specific way."
            )

        record_activity("faq_question_submitted", {"message_length": len(user_message)})
        return _ask_render(
            user_name,
            faq_response=faq_response,
            faq_error=None,
            user_message=user_message,
        )

    except FileNotFoundError as error:
        app.logger.exception("FAQ data file missing: %s", error)
        return _ask_render(
            user_name,
            faq_response=(
                "HerSignal could not access its FAQ data right now. "
                "Please try again shortly."
            ),
            faq_error="The FAQ support data could not be loaded.",
            user_message=request.form.get("user_message", "").strip(),
            status=500,
        )

    except Exception as error:
        app.logger.exception("Error processing FAQ question: %s", error)
        return _ask_render(
            user_name,
            faq_response=(
                "Something went wrong while HerSignal was preparing your response. "
                "Please try again."
            ),
            faq_error="HerSignal could not process that question just now.",
            user_message=request.form.get("user_message", "").strip(),
            status=500,
        )


@app.route("/my-insights")
@login_required
def my_insights():
    uid = session["user_id"]
    try:
        rows_desc = (
            InsightSnapshot.query.filter_by(user_id=uid)
            .order_by(InsightSnapshot.created_at.desc())
            .limit(40)
            .all()
        )
        entries = snapshots_with_deltas(rows_desc)
        rows_asc = list(reversed(rows_desc))
        sparklines = sparkline_specs(rows_asc)
        snapshot_options = snapshot_select_options(rows_desc)

        compare_a = request.args.get("a", type=int)
        compare_b = request.args.get("b", type=int)
        compare_select_a = compare_a
        compare_select_b = compare_b
        if len(snapshot_options) >= 2:
            if compare_select_a is None:
                compare_select_a = snapshot_options[0]["id"]
            if compare_select_b is None:
                compare_select_b = snapshot_options[1]["id"]
            if compare_select_a == compare_select_b:
                compare_select_b = snapshot_options[1]["id"]

        compare_data = None
        compare_error = None
        if compare_a and compare_b:
            if compare_a == compare_b:
                compare_error = "Choose two different snapshots to compare."
            else:
                sa = InsightSnapshot.query.filter_by(id=compare_a, user_id=uid).first()
                sb = InsightSnapshot.query.filter_by(id=compare_b, user_id=uid).first()
                if not sa or not sb:
                    compare_error = "One or both snapshots could not be found."
                else:
                    earlier, later = (sa, sb) if sa.created_at <= sb.created_at else (sb, sa)
                    dh = round(later.hormonal - earlier.hormonal, 2)
                    dm = round(later.metabolic - earlier.metabolic, 2)
                    di = round(later.inflammatory - earlier.inflammatory, 2)
                    compare_data = {
                        "earlier": earlier,
                        "later": later,
                        "dh": dh,
                        "dm": dm,
                        "di": di,
                        "dh_display": format_delta(dh),
                        "dm_display": format_delta(dm),
                        "di_display": format_delta(di),
                    }

        return render_template(
            "my_insights.html",
            entries=entries,
            sparklines=sparklines,
            snapshot_options=snapshot_options,
            compare=compare_data,
            compare_error=compare_error,
            compare_select_a=compare_select_a,
            compare_select_b=compare_select_b,
            load_error=None,
            **_insights_layout(),
        )
    except Exception as exc:
        app.logger.exception("Failed to load my-insights for user %s: %s", uid, exc)
        return render_template(
            "my_insights.html",
            entries=[],
            sparklines={},
            snapshot_options=[],
            compare=None,
            compare_error=None,
            compare_select_a=None,
            compare_select_b=None,
            load_error=(
                "HerSignal could not load your insights timeline. "
                "Try refreshing the page. If this keeps happening, stop the app and run it again from the project folder."
            ),
            **_insights_layout(),
        ), 500


@app.route("/retake", methods=["GET", "POST"])
@login_required
def retake_insight():
    """
    Shorter follow-up questionnaire for logged-in users with at least one saved insight.
    Does not touch session keys used by baseline PDF export.
    """
    uid = session["user_id"]
    user_name = session.get("user_name", "").strip()
    baseline_questions = load_symptom_questions()
    retake_questions = load_symptom_questions(RETAKE_QUESTIONS_PATH)

    prev = _latest_insight_for_user(uid)
    if not prev:
        return redirect(url_for("my_insights", retake="need_insight"))

    if request.method == "GET":
        return render_template(
            "retake.html",
            questions=retake_questions,
            previous_insight=prev,
            user_name=user_name,
            symptom_error=None,
            submitted_answers=None,
            **_retake_layout(),
        )

    if not retake_questions:
        return (
            render_template(
                "retake.html",
                questions=[],
                previous_insight=prev,
                user_name=user_name,
                symptom_error="The follow-up questionnaire could not be loaded right now.",
                submitted_answers=None,
                **_retake_layout(),
            ),
            500,
        )

    submitted_answers = {}
    responses = {}
    for item in retake_questions:
        sid = item["id"]
        raw = request.form.get(sid, "").strip()
        submitted_answers[sid] = raw
        norm_ans = normalise_response(raw)
        if norm_ans not in {"yes", "no", "maybe"}:
            return render_template(
                "retake.html",
                questions=retake_questions,
                previous_insight=prev,
                user_name=user_name,
                symptom_error="Please answer every question using yes, no, or maybe.",
                submitted_answers=submitted_answers,
                **_retake_layout(),
            )
        responses[sid] = norm_ans

    scores = calculate_category_scores(responses, questions=retake_questions)
    prev_q = _questions_for_normalizing_snapshot(prev, baseline_questions, retake_questions)
    max_prev = max_possible_category_scores(prev_q)
    max_new = max_possible_category_scores(retake_questions)

    raw_prev = {
        "hormonal": float(prev.hormonal),
        "metabolic": float(prev.metabolic),
        "inflammatory": float(prev.inflammatory),
    }
    norm_prev = normalize_scores_unit_interval(raw_prev, max_prev)
    norm_new = normalize_scores_unit_interval(scores, max_new)
    deltas = normalized_deltas(norm_new, norm_prev)

    trends = build_category_trends(norm_prev, norm_new)
    category_sentences = build_category_interpretation_sentences(trends)
    overall_summary = build_overall_pattern_summary(trends)
    dominant_note = dominant_pattern_note(prev.dominant_label, dominant_category_label(scores))
    reflection_bullets = followup_reflection_bullets(retake_questions, responses)

    saved_insight = False
    try:
        snap = InsightSnapshot(
            user_id=uid,
            hormonal=float(scores.get("hormonal", 0)),
            metabolic=float(scores.get("metabolic", 0)),
            inflammatory=float(scores.get("inflammatory", 0)),
            dominant_label=dominant_category_label(scores),
            test_type="retake",
        )
        db.session.add(snap)
        db.session.commit()
        saved_insight = True
        record_activity("retake_completed", {"snapshot_id": snap.id})
    except Exception as exc:
        db.session.rollback()
        app.logger.warning("Could not save retake snapshot: %s", exc)

    norm_delta_display = {
        "hormonal": format_delta(deltas["hormonal"]),
        "metabolic": format_delta(deltas["metabolic"]),
        "inflammatory": format_delta(deltas["inflammatory"]),
    }

    return render_template(
        "follow_up_results.html",
        user_name=user_name,
        previous_insight=prev,
        previous_raw=raw_prev,
        current_raw=scores,
        max_previous=max_prev,
        max_current=max_new,
        previous_normalized=norm_prev,
        current_normalized=norm_new,
        norm_deltas=deltas,
        norm_delta_display=norm_delta_display,
        category_trends=trends,
        category_sentences=category_sentences,
        overall_summary=overall_summary,
        dominant_note=dominant_note,
        reflection_bullets=reflection_bullets,
        saved_insight=saved_insight,
        **_results_layout(
            hero_title="Follow-up comparison",
            hero_subtitle="Scaled educational comparison with your previous saved insight.",
            hero_id="followup-hero-title",
        ),
    )


@app.route("/symptoms")
def symptoms_page():
    """
    Render the symptom checker page with all questionnaire items.
    """
    user_name = session.get("user_name", "").strip()

    try:
        questions = load_symptom_questions()

        if not questions:
            return render_template(
                "symptoms.html",
                questions=[],
                submitted_answers=None,
                symptom_error="The symptom questions could not be loaded right now. Please try again later.",
                user_name=user_name,
                **_symptom_layout(),
            ), 500

        return render_template(
            "symptoms.html",
            questions=questions,
            submitted_answers=None,
            symptom_error=None,
            user_name=user_name,
            **_symptom_layout(),
        )

    except FileNotFoundError as error:
        app.logger.exception("Symptom questions file missing: %s", error)
        return render_template(
            "symptoms.html",
            questions=[],
            submitted_answers=None,
            symptom_error="The symptom question file is missing at the moment.",
            user_name=user_name,
            **_symptom_layout(),
        ), 500

    except Exception as error:
        app.logger.exception("Error loading symptom page: %s", error)
        return render_template(
            "symptoms.html",
            questions=[],
            submitted_answers=None,
            symptom_error="HerSignal could not load the symptom checker just now. Please try again.",
            user_name=user_name,
            **_symptom_layout(),
        ), 500


@app.route("/symptom-checker", methods=["POST"])
def symptom_checker():
    """
    Process symptom questionnaire responses and render the structured results page.
    """
    user_name = session.get("user_name", "").strip()
    submitted_answers = {}

    try:
        questions = load_symptom_questions()

        if not questions:
            return render_template(
                "symptoms.html",
                questions=[],
                submitted_answers=None,
                symptom_error="The symptom questions could not be loaded right now. Please try again later.",
                user_name=user_name,
                **_symptom_layout(),
            ), 500

        responses = {}

        for item in questions:
            symptom_id = item["id"]
            raw_answer = request.form.get(symptom_id, "").strip()
            normalised = normalise_response(raw_answer)
            submitted_answers[symptom_id] = raw_answer

            if normalised not in {"yes", "no", "maybe"}:
                return render_template(
                    "symptoms.html",
                    questions=questions,
                    submitted_answers=submitted_answers,
                    symptom_error="Please answer every question using yes, no, or maybe.",
                    user_name=user_name,
                    **_symptom_layout(),
                )

            responses[symptom_id] = normalised

        scores = calculate_category_scores(responses)

        if not isinstance(scores, dict):
            raise ValueError("Category scores were not returned in dictionary format.")

        result_data = generate_result_data(scores, responses)

        if not isinstance(result_data, dict):
            raise ValueError("Result data was not returned in dictionary format.")

        try:
            chart_path = build_symptom_chart(scores)
        except Exception as chart_error:
            app.logger.exception("Chart generation failed: %s", chart_error)
            chart_path = None

        session["latest_scores"] = scores
        session["latest_result_data"] = result_data
        session["latest_chart_path"] = chart_path
        session["latest_export_date"] = datetime.now().strftime("%d %B %Y")

        record_activity(
            "symptom_check_completed",
            {
                "hormonal": scores.get("hormonal"),
                "metabolic": scores.get("metabolic"),
                "inflammatory": scores.get("inflammatory"),
                "chart_generated": bool(chart_path),
            },
        )

        saved_insight = False
        if session.get("user_id"):
            try:
                snap = InsightSnapshot(
                    user_id=session["user_id"],
                    hormonal=float(scores.get("hormonal", 0)),
                    metabolic=float(scores.get("metabolic", 0)),
                    inflammatory=float(scores.get("inflammatory", 0)),
                    dominant_label=dominant_category_label(scores),
                    test_type="baseline",
                )
                db.session.add(snap)
                db.session.commit()
                saved_insight = True
                record_activity("insight_snapshot_saved", {"snapshot_id": snap.id})
            except Exception as snap_error:
                db.session.rollback()
                app.logger.warning("Could not save insight snapshot: %s", snap_error)

        return render_template(
            "results.html",
            scores=scores,
            result_data=result_data,
            chart_path=chart_path,
            user_name=user_name,
            saved_insight=saved_insight,
            **_results_layout(),
        )

    except FileNotFoundError as error:
        app.logger.exception("Required symptom-processing file missing: %s", error)
        return render_template(
            "symptoms.html",
            questions=[],
            submitted_answers=submitted_answers,
            symptom_error="HerSignal could not access one of the files needed to process your answers.",
            user_name=user_name,
            **_symptom_layout(),
        ), 500

    except ValueError as error:
        app.logger.exception("Validation or data structure error in symptom checker: %s", error)
        return render_template(
            "symptoms.html",
            questions=load_symptom_questions() if callable(load_symptom_questions) else [],
            submitted_answers=submitted_answers,
            symptom_error="HerSignal could not organise your responses properly. Please try again.",
            user_name=user_name,
            **_symptom_layout(),
        ), 500

    except Exception as error:
        app.logger.exception("Unexpected error in symptom checker: %s", error)
        return render_template(
            "symptoms.html",
            questions=load_symptom_questions() if callable(load_symptom_questions) else [],
            submitted_answers=submitted_answers,
            symptom_error="Something went wrong while generating your insight. Please try again.",
            user_name=user_name,
            **_symptom_layout(),
        ), 500


@app.route("/export-results")
def export_results():
    """
    Export the user's latest result as a downloadable PDF summary.
    """
    try:
        scores = session.get("latest_scores")
        result_data = session.get("latest_result_data")
        chart_path = session.get("latest_chart_path")
        export_date = session.get("latest_export_date", datetime.now().strftime("%d %B %Y"))
        user_name = session.get("user_name", "").strip()

        if not scores or not result_data:
            return render_template(
                "index.html",
                faq_response=(
                    "There are no symptom results available to export yet. "
                    "Please complete the symptom checker first."
                ),
                faq_error="No result summary is available for export.",
                user_name=user_name,
                user_message=None
            )

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        left_margin = 50
        y = height - 60

        pdf.setTitle("HerSignal: Your Symptom Insight Summary")

        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(left_margin, y, "HerSignal Educational Summary")
        y -= 30

        pdf.setFont("Helvetica", 11)
        name_text = user_name if user_name else "Not provided"
        pdf.drawString(left_margin, y, f"Name: {name_text}")
        y -= 18
        pdf.drawString(left_margin, y, f"Date: {export_date}")
        y -= 28

        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(left_margin, y, "HerSignal Introduction")
        y -= 18

        pdf.setFont("Helvetica", 11)
        y = draw_wrapped_text(
            pdf,
            result_data.get("page_intro", ""),
            left_margin,
            y,
            max_chars=95,
            line_height=15
        )
        y -= 18

        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(left_margin, y, "Category Scores")
        y -= 20

        pdf.setFont("Helvetica", 11)
        pdf.drawString(left_margin, y, f"Hormonal: {scores.get('hormonal', 0)}")
        y -= 16
        pdf.drawString(left_margin, y, f"Metabolic: {scores.get('metabolic', 0)}")
        y -= 16
        pdf.drawString(left_margin, y, f"Inflammatory: {scores.get('inflammatory', 0)}")
        y -= 28

        if chart_path:
            chart_full_path = os.path.join(app.static_folder, chart_path)

            if os.path.exists(chart_full_path):
                try:
                    if y < 260:
                        pdf.showPage()
                        y = height - 60

                    pdf.setFont("Helvetica-Bold", 13)
                    pdf.drawString(left_margin, y, "Symptom Pattern Chart")
                    y -= 20

                    chart_image = ImageReader(chart_full_path)

                    image_width = 250
                    image_height = 250

                    pdf.drawImage(
                        chart_image,
                        left_margin,
                        y - image_height,
                        width=image_width,
                        height=image_height,
                        preserveAspectRatio=True,
                        mask='auto'
                    )

                    y -= image_height + 24

                except Exception as chart_error:
                    app.logger.exception("Could not add chart to PDF export: %s", chart_error)

                    if y < 120:
                        pdf.showPage()
                        y = height - 60

                    pdf.setFont("Helvetica-Bold", 13)
                    pdf.drawString(left_margin, y, "Symptom Pattern Chart")
                    y -= 18
                    pdf.setFont("Helvetica", 11)
                    y = draw_wrapped_text(
                        pdf,
                        "The chart could not be included in this export, but your written result summary has still been provided below.",
                        left_margin,
                        y,
                        max_chars=95,
                        line_height=15
                    )
                    y -= 14

        sections = [
            ("Pattern Overlap Notes", result_data.get("pattern_overlap_note", "")),
            ("Pattern Chart Explanation", result_data.get("chart_explanation", "")),
            ("What This May Mean in Your PCOS Pattern", result_data.get("why_hersignal_presented_response", "")),
            ("Helpful and Useful Note", result_data.get("friendly_note", "")),
            ("General Disclaimer", result_data.get("general_disclaimer", "")),
            ("Supplement Disclaimer", result_data.get("supplement_disclaimer", "")),
        ]

        for heading, content in sections:
            if y < 120:
                pdf.showPage()
                y = height - 60

            pdf.setFont("Helvetica-Bold", 13)
            pdf.drawString(left_margin, y, heading)
            y -= 18

            pdf.setFont("Helvetica", 11)
            y = draw_wrapped_text(pdf, content, left_margin, y, max_chars=95, line_height=15)
            y -= 14

        supplement_notes = result_data.get("supplement_notes", [])
        if supplement_notes:
            if y < 140:
                pdf.showPage()
                y = height - 60

            pdf.setFont("Helvetica-Bold", 13)
            pdf.drawString(left_margin, y, "Helpful Supplements")
            y -= 20

            pdf.setFont("Helvetica", 11)
            for note in supplement_notes:
                note_text = f"{note.get('name', '')}: {note.get('summary', '')}"
                warning = note.get("warning", "").strip()
                if warning:
                    note_text += f" Warning: {warning}"

                y = draw_wrapped_text(pdf, f"- {note_text}", left_margin, y, max_chars=92, line_height=15)
                y -= 10

                if y < 100:
                    pdf.showPage()
                    y = height - 60
                    pdf.setFont("Helvetica", 11)

        pdf.save()
        buffer.seek(0)

        filename = "hersignal_summary.pdf"
        record_activity("pdf_export")
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf"
        )

    except Exception as error:
        app.logger.exception("Error exporting results PDF: %s", error)
        user_name = session.get("user_name", "").strip()

        return render_template(
            "results.html",
            scores=session.get("latest_scores", {"hormonal": 0, "metabolic": 0, "inflammatory": 0}),
            result_data=session.get(
                "latest_result_data",
                {
                    "page_title": "Your Symptom Pattern Results",
                    "page_intro": "HerSignal could not prepare the export, but your latest result is still shown below.",
                    "contributing_intro": "",
                    "contributing_symptoms": [],
                    "pattern_overlap_note": "The export could not be generated just now.",
                    "why_hersignal_presented_response": "",
                    "supplement_intro": "",
                    "supplement_notes": [],
                    "chart_explanation": "",
                    "friendly_note": "Please try exporting again.",
                    "general_disclaimer": "HerSignal is an educational support system only.",
                    "supplement_disclaimer": "Supplement information is educational only."
                }
            ),
            chart_path=session.get("latest_chart_path"),
            user_name=user_name,
            saved_insight=False,
            **_results_layout(),
        ), 500


@app.errorhandler(404)
def page_not_found(error):
    """
    Handle page not found errors.
    """
    app.logger.warning("404 error: %s", error)
    user_name = session.get("user_name", "").strip()

    return render_template(
        "index.html",
        faq_response="That page could not be found. Please return to the main HerSignal pages and try again.",
        faq_error="The page you tried to open does not exist.",
        user_name=user_name,
        user_message=None,
        **_layout(chat=True, hero_variant="landing", hero_id="site-title"),
    ), 404


@app.errorhandler(500)
def internal_server_error(error):
    """
    Handle unexpected internal server errors.
    """
    app.logger.exception("500 error: %s", error)
    user_name = session.get("user_name", "").strip()

    return render_template(
        "index.html",
        faq_response="HerSignal ran into a problem while processing that request. Please try again.",
        faq_error="An unexpected server error occurred.",
        user_name=user_name,
        user_message=None,
        **_layout(chat=True, hero_variant="landing", hero_id="site-title"),
    ), 500


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").strip().lower() == "true"
    app.run(debug=debug_mode)