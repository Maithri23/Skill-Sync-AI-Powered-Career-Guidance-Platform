import json
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from models import db, Job

jobs_bp = Blueprint("jobs", __name__)

@jobs_bp.route("/")
@login_required
def board():
    jobs = Job.query.filter_by(user_id=current_user.id).all()
    return render_template("job_tracker.html", jobs=[{
        "id": j.id, "title": j.title, "company": j.company, "url": j.url,
        "status": j.status, "notes": j.notes
    } for j in jobs])

@jobs_bp.route("/api", methods=["POST"])
@login_required
def create_job():
    data = request.get_json(force=True)
    j = Job(user_id=current_user.id, title=data.get("title",""), company=data.get("company",""), status=data.get("status","To Apply"))
    db.session.add(j); db.session.commit()
    return {"id": j.id}

@jobs_bp.route("/api/<int:job_id>", methods=["PATCH"])
@login_required
def update_job(job_id):
    j = Job.query.filter_by(id=job_id, user_id=current_user.id).first_or_404()
    data = request.get_json(force=True)
    for k in ["title","company","url","status","notes"]:
        if k in data: setattr(j, k, data[k])
    db.session.commit()
    return {"ok": True}

@jobs_bp.route("/api/<int:job_id>", methods=["DELETE"])
@login_required
def delete_job(job_id):
    j = Job.query.filter_by(id=job_id, user_id=current_user.id).first_or_404()
    db.session.delete(j); db.session.commit()
    return {"ok": True}
