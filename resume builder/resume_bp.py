import json, uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from models import db, Resume
from utils import render_resume_html, html_to_pdf, html_to_docx, html_to_txt, sanitize_resume_payload

resume_bp = Blueprint("resumes", __name__)

DEFAULT_SECTIONS = {
  "personal": {"full_name":"", "email":"", "phone":"", "location":"", "website":"", "linkedin":"", "github":""},
  "summary": {"text": ""},
  "experience": [{"title":"", "company":"", "start":"", "end":"", "desc":""}],
  "education": [{"degree":"", "school":"", "year":"", "details":""}],
  "projects": [{"name":"", "link":"", "desc":""}],
  "skills": ["Python","Flask","SQL"],
  "certifications": [{"name":"", "issuer":"", "year":""}],
  "achievements": [""]
}
DEFAULT_ORDER = ["personal","summary","experience","education","projects","skills","certifications","achievements"]

@resume_bp.route("/new")
@login_required
def new():
    profile = current_user.get_profile() or {}
    data = json.loads(json.dumps(DEFAULT_SECTIONS))  # deep copy
    if profile:
        data["personal"] = profile.get("personal", data["personal"])
        data["summary"]["text"] = profile.get("summary","")
        data["skills"] = profile.get("skills", data["skills"])
    r = Resume(user_id=current_user.id, title="My Resume", data_json=json.dumps(data), order_json=json.dumps(DEFAULT_ORDER))
    db.session.add(r); db.session.commit()
    return redirect(url_for("resumes.editor", resume_id=r.id))

@resume_bp.route("/<int:resume_id>")
@login_required
def editor(resume_id):
    r = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
    return render_template("editor.html", r=r, payload=json.loads(r.data_json or "{}"), order=json.loads(r.order_json or "[]"))

@resume_bp.route("/<int:resume_id>/preview")
@login_required
def preview(resume_id):
    r = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
    return render_resume_html(r, sanitize=True)

@resume_bp.route("/<int:resume_id>/delete", methods=["POST"])
@login_required
def delete(resume_id):
    r = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
    db.session.delete(r); db.session.commit()
    flash("Deleted resume.", "success")
    return redirect(url_for("dashboard"))

@resume_bp.route("/<int:resume_id>/duplicate", methods=["POST"])
@login_required
def duplicate(resume_id):
    r = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
    new_r = Resume(user_id=current_user.id, title=r.title + " (Copy)", template=r.template, theme_color=r.theme_color,
                   font_family=r.font_family, order_json=r.order_json, data_json=r.data_json)
    db.session.add(new_r); db.session.commit()
    return redirect(url_for("resumes.editor", resume_id=new_r.id))

@resume_bp.route("/<int:resume_id>/export/<fmt>")
@login_required
def export(resume_id, fmt):
    r = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
    # sanitize payload to ensure no empty sections
    html = render_resume_html(r, sanitize=True)
    if fmt == "pdf":
        return send_file(html_to_pdf(html), mimetype="application/pdf", as_attachment=True, download_name=f"{r.title}.pdf")
    if fmt == "docx":
        return send_file(html_to_docx(html), mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document", as_attachment=True, download_name=f"{r.title}.docx")
    if fmt == "txt":
        return send_file(html_to_txt(html, r.title), mimetype="text/plain", as_attachment=True, download_name=f"{r.title}.txt")
    return ("Unknown format", 400)

@resume_bp.route("/api/<int:resume_id>", methods=["POST","PATCH"])
@login_required
def save_api(resume_id):
    r = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
    data = request.get_json(force=True, silent=True) or {}
    changed = False
    if "data" in data:
        r.data_json = json.dumps(data["data"]); changed=True
    if "order" in data:
        r.order_json = json.dumps(data["order"]); changed=True
    if "template" in data:
        r.template = data["template"]; changed=True
    if "theme_color" in data:
        r.theme_color = data["theme_color"]; changed=True
    if "font_family" in data:
        r.font_family = data["font_family"]; changed=True
    if changed:
        db.session.commit()
    return {"ok": True}

@resume_bp.route("/api/<int:resume_id>/sync-from-profile", methods=["POST"])
@login_required
def sync_from_profile(resume_id):
    r = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
    payload = json.loads(r.data_json or "{}")
    prof = current_user.get_profile() or {}
    payload["personal"] = prof.get("personal", payload.get("personal", {}))
    payload["summary"]["text"] = prof.get("summary", payload.get("summary",{}).get("text",""))
    payload["skills"] = prof.get("skills", payload.get("skills", []))
    r.data_json = json.dumps(payload); db.session.commit()
    return {"ok": True, "data": payload}

@resume_bp.route("/shared/<share_uuid>")
def shared_view(share_uuid):
    r = Resume.query.filter_by(share_uuid=share_uuid).first_or_404()
    html = render_resume_html(r, sanitize=True)
    return render_template("resume_public.html", html=html, title=r.title)
