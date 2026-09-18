import os
from functools import wraps

from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-this")

# Neon provides DATABASE_URL. SQLAlchemy/psycopg handles the PostgreSQL connection.
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///streetlens.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)


class Inspection(db.Model):
    __tablename__ = "inspections"

    id = db.Column(db.Integer, primary_key=True)
    route = db.Column(db.String(100), nullable=False, default="US-1")
    mile_post = db.Column(db.Float, nullable=False, default=52.1)
    direction = db.Column(db.String(50), nullable=False, default="Northbound")
    distress_index = db.Column(db.Integer, nullable=False, default=71)
    condition = db.Column(db.String(50), nullable=False, default="POOR")
    captured_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)


DISTRESS = [
    {"label": "Alligator crack", "pct": 62, "color": "#3b82f6", "sub": "Avg width 5mm · high density"},
    {"label": "Longitudinal", "pct": 21, "color": "#f97316", "sub": "Total length 8.5m · stable"},
    {"label": "Transverse", "pct": 11, "color": "#eab308", "sub": "4 cracks · 10m avg spacing"},
    {"label": "Pothole", "pct": 6, "color": "#a855f7", "sub": "1 count · 25mm depth"},
]

PILLS = [
    {"label": "Longitudinal", "score": 78},
    {"label": "Alligator", "score": 81},
    {"label": "Transverse", "score": 84},
    {"label": "Pothole", "score": 91},
]


def init_db():
    """Create tables the first time the deployed app needs the database."""
    with app.app_context():
        db.create_all()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "info")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html", screen="login")


@app.route("/register", methods=["POST"])
def register():
    init_db()

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if len(username) < 3 or len(username) > 32:
        flash("Username must be between 3 and 32 characters.", "error")
        return redirect(url_for("login") + "#register")

    if not email or "@" not in email:
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("login") + "#register")

    if len(password) < 8:
        flash("Password must contain at least 8 characters.", "error")
        return redirect(url_for("login") + "#register")

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("login") + "#register")

    if User.query.filter_by(username=username).first():
        flash("That username is already registered.", "error")
        return redirect(url_for("login") + "#register")

    if User.query.filter_by(email=email).first():
        flash("That email is already registered.", "error")
        return redirect(url_for("login") + "#register")

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.commit()

    flash("Account created successfully. You can now sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["POST"])
def login_submit():
    init_db()

    identifier = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    user = User.query.filter(
        db.or_(User.username == identifier, User.email == identifier.lower())
    ).first()

    if not user or not check_password_hash(user.password_hash, password):
        flash("Invalid username/email or password.", "error")
        return redirect(url_for("login"))

    session.clear()
    session["user_id"] = user.id
    session["username"] = user.username

    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    init_db()

    latest = Inspection.query.order_by(Inspection.id.desc()).first()

    # Keep the current UI values when no inspection has been stored yet.
    inspection = latest or {
        "route": "US-1",
        "mile_post": 52.1,
        "direction": "Northbound",
        "distress_index": 71,
        "condition": "POOR",
    }

    return render_template(
        "index.html",
        screen="dashboard",
        distress=DISTRESS,
        pills=PILLS,
        inspection=inspection,
        username=session.get("username"),
    )


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


# Vercel imports `app` from api/index.py. Local development still works.
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
