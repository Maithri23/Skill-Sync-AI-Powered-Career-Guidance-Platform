from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from models import db, CoverLetter
from utils import html_to_pdf, html_to_docx, html_to_txt

cover_bp = Blueprint("cover", __name__)

@cover_bp.route("/new")
@login_required
def new():
    cl = CoverLetter(user_id=current_user.id, title="New Cover Letter", body="Dear Hiring Manager,\n\nI am excited to apply ...\n\nSincerely,")
    db.session.add(cl); db.session.commit()
    return redirect(url_for("cover.edit", cl_id=cl.id))

@cover_bp.route("/<int:cl_id>", methods=["GET", "POST"])
@login_required
def edit(cl_id):
    cl = CoverLetter.query.filter_by(id=cl_id, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        cl.title = request.form.get("title", cl.title)
        cl.body = request.form.get("body", cl.body)
        cl.theme_color = request.form.get("theme_color", cl.theme_color)
        cl.font_family = request.form.get("font_family", cl.font_family)
        db.session.commit()
        flash("Saved cover letter", "success")
    return render_template("cover_letter.html", cl=cl)

@cover_bp.route("/<int:cl_id>/export/<fmt>")
@login_required
def export(cl_id, fmt):
    cl = CoverLetter.query.filter_by(id=cl_id, user_id=current_user.id).first_or_404()
    html = render_template("cover_letter_export.html", cl=cl)
    if fmt == "pdf":
        return send_file(html_to_pdf(html), mimetype="application/pdf", as_attachment=True, download_name=f"{cl.title}.pdf")
    if fmt == "docx":
        return send_file(html_to_docx(html), mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document", as_attachment=True, download_name=f"{cl.title}.docx")
    if fmt == "txt":
        return send_file(html_to_txt(html, cl.title), mimetype="text/plain", as_attachment=True, download_name=f"{cl.title}.txt")
    return ("Unknown format", 400)
