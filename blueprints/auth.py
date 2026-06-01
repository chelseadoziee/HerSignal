import re

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from activity_log import record_activity
from database import db
from models import User

auth_bp = Blueprint("auth", __name__)

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
# pbkdf2 works on all supported Python builds; scrypt often fails on macOS LibreSSL builds
_PASSWORD_METHOD = "pbkdf2:sha256"


def _normalise_username(value):
    return (value or "").strip().lower()


def _hash_password(password):
    return generate_password_hash(password, method=_PASSWORD_METHOD)


def _verify_password(stored_hash, password):
    if not stored_hash or not password:
        return False
    try:
        return check_password_hash(stored_hash, password)
    except AttributeError:
        # Werkzeug scrypt hashes cannot be checked when hashlib.scrypt is unavailable
        current_app.logger.warning(
            "Password verification skipped: hash method not supported on this runtime"
        )
        return False


def _legacy_scrypt_hash(stored_hash):
    return isinstance(stored_hash, str) and stored_hash.startswith("scrypt:")


def _auth_layout(**kwargs):
    """Layout context for login/register (no journey strip)."""
    base = {
        "show_journey": False,
        "show_disclaimer": True,
        "hero_variant": "compact",
        "hero_id": "page-hero-title",
    }
    base.update(kwargs)
    return base


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = _normalise_username(request.form.get("username", ""))
        password = request.form.get("password", "") or ""

        if not _USERNAME_RE.match(username):
            error = (
                "Username must be 3–32 characters and use only letters, numbers, "
                "or underscores."
            )
        elif len(password) < 8:
            error = "Password must be at least 8 characters."

        if error:
            return render_template(
                "register.html",
                error=error,
                username=username,
                **_auth_layout(
                    page_title="Register — HerSignal",
                    hero_title="Create your account",
                    hero_subtitle="Save insights and track how your educational scores change over time.",
                ),
            )

        existing = User.query.filter_by(username=username).first()
        if existing:
            if _legacy_scrypt_hash(existing.password_hash):
                # Account created before pbkdf2 fix; allow setting a new password on re-register
                existing.password_hash = _hash_password(password)
                db.session.commit()
                session["user_id"] = existing.id
                session["user_name"] = existing.username
                session.permanent = True
                record_activity("register_password_reset", {"username_length": len(username)})
                return redirect(url_for("home"))
            error = "That username is already taken. Try another or log in."
            return render_template(
                "register.html",
                error=error,
                username=username,
                **_auth_layout(
                    page_title="Register — HerSignal",
                    hero_title="Create your account",
                    hero_subtitle="Save insights and track how your educational scores change over time.",
                ),
            )

        user = User(
            username=username,
            password_hash=_hash_password(password),
        )
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        session["user_name"] = user.username
        session.permanent = True
        record_activity("register", {"username_length": len(username)})
        return redirect(url_for("home"))

    return render_template(
        "register.html",
        error=None,
        username="",
        **_auth_layout(
            page_title="Register — HerSignal",
            hero_title="Create your account",
            hero_subtitle="Save insights and track how your educational scores change over time.",
        ),
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = _normalise_username(request.form.get("username", ""))
        password = request.form.get("password", "") or ""

        try:
            user = User.query.filter_by(username=username).first()
        except Exception as exc:
            current_app.logger.exception("Database error during login lookup: %s", exc)
            error = "HerSignal could not reach the account database. Please try again in a moment."
            return render_template(
                "login.html",
                error=error,
                username=username,
                **_auth_layout(
                    page_title="Log in — HerSignal",
                    hero_title="Welcome back",
                    hero_subtitle="Sign in to access your private insights timeline.",
                ),
            )

        if user and _legacy_scrypt_hash(user.password_hash):
            error = (
                "This account was saved with an older password format that no longer works here. "
                "Go to Register, enter the same username and a new password (8+ characters) to "
                "restore access—your insight history is kept."
            )
            return render_template(
                "login.html",
                error=error,
                username=username,
                **_auth_layout(
                    page_title="Log in — HerSignal",
                    hero_title="Welcome back",
                    hero_subtitle="Sign in to access your private insights timeline.",
                ),
            )

        if not user or not _verify_password(user.password_hash, password):
            error = "Username or password was not recognised."
            return render_template(
                "login.html",
                error=error,
                username=username,
                **_auth_layout(
                    page_title="Log in — HerSignal",
                    hero_title="Welcome back",
                    hero_subtitle="Sign in to access your private insights timeline.",
                ),
            )

        session["user_id"] = user.id
        session["user_name"] = user.username
        session.permanent = True
        record_activity("login", {"username_length": len(username)})
        next_url = request.args.get("next") or url_for("home")
        if not next_url.startswith("/") or next_url.startswith("//"):
            next_url = url_for("home")
        return redirect(next_url)

    return render_template(
        "login.html",
        error=None,
        username="",
        **_auth_layout(
            page_title="Log in — HerSignal",
            hero_title="Welcome back",
            hero_subtitle="Sign in to access your private insights timeline.",
        ),
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():
    if session.get("user_id"):
        record_activity("logout")
    session.pop("user_id", None)
    session.pop("user_name", None)
    return redirect(url_for("home"))
