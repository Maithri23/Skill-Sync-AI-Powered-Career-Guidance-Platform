from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from models import db, User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password", "error")
        else:
            login_user(user)
            return redirect(url_for("dashboard"))
    return render_template("auth_login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        name = request.form.get("name","").strip()
        password = request.form.get("password","")
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
        elif not email or not name or not password:
            flash("Please fill all fields.", "error")
        else:
            u = User(email=email, name=name)
            u.set_password(password)
            db.session.add(u)
            db.session.commit()
            flash("Registered. Please log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth_register.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
