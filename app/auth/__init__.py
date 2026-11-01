import re
import sqlite3
from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from ..models import User


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _login_destination():
    target = request.form.get('next') or request.args.get('next', '')
    if target.startswith('/') and not target.startswith('//') and len(target) <= 2048 and '\\' not in target and not any(ord(c)<32 or ord(c)==127 for c in target):
        parsed = urlsplit(target)
        if not parsed.scheme and not parsed.netloc:
            return target
    return url_for('main.dashboard')


def _sign_in(user):
    # Drop state belonging to any prior account before establishing this login.
    session.clear()
    login_user(user)


@auth_bp.route("/register", methods=("GET", "POST"))
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        error = None
        if not name:
            error = "Please enter your name."
        elif len(name) > 60:
            error = "Your name must be 60 characters or fewer."
        elif not EMAIL_PATTERN.match(email):
            error = "Please enter a valid email address."
        elif len(password) < 8:
            error = "Your password must be at least 8 characters."
        elif password != confirm_password:
            error = "The passwords do not match."
        elif User.get_by_email(email) is not None:
            error = "An account with that email already exists."

        if error is None:
            try:
                user = User.create(name, email, generate_password_hash(password))
            except sqlite3.IntegrityError:
                error = "An account with that email already exists."
            else:
                _sign_in(user)
                flash("Your account has been created. Welcome to IELTS Platform!", "success")
                return redirect(url_for("main.dashboard"))

        flash(error, "error")

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=("GET", "POST"))
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.get_by_email(email)

        if user is None or not check_password_hash(user.password_hash, password):
            flash("Email or password is incorrect.", "error")
        else:
            _sign_in(user)
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(_login_destination())

    return render_template("auth/login.html")


@auth_bp.route("/admin-login", methods=("GET", "POST"))
def admin_login():
    """Sign in through the dedicated administrator entry point."""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.index"))
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.get_by_email(email)

        if (
            user is None
            or not user.is_admin
            or not check_password_hash(user.password_hash, password)
        ):
            flash("Admin username or password is incorrect.", "error")
        else:
            _sign_in(user)
            flash("Welcome to the admin panel.", "success")
            return redirect(url_for("admin.index"))

    return render_template("auth/admin_login.html")


@auth_bp.route("/logout", methods=("POST",))
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.index"))
