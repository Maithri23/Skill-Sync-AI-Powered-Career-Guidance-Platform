import os
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from models import db, User, Resume, CoverLetter, Job
from auth import auth_bp
from profile_bp import profile_bp
from resume_bp import resume_bp
from cover_bp import cover_bp
from jobs_bp import jobs_bp

def create_app():
    app = Flask(__name__, instance_relative_config=True, static_folder="static", template_folder="templates")
    os.makedirs(app.instance_path, exist_ok=True)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Auto-create DB tables on startup (safe for SQLite dev)
    with app.app_context():
        db.create_all()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(resume_bp, url_prefix="/resumes")
    app.register_blueprint(cover_bp, url_prefix="/cover-letters")
    app.register_blueprint(jobs_bp, url_prefix="/jobs")

    @app.route("/")
    @login_required
    def dashboard():
        resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.updated_at.desc()).all()
        covers = CoverLetter.query.filter_by(user_id=current_user.id).order_by(CoverLetter.updated_at.desc()).all()
        jobs = Job.query.filter_by(user_id=current_user.id).all()
        return render_template("dashboard.html", resumes=resumes, covers=covers, jobs=jobs)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
