from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

profile_bp = Blueprint("profile", __name__)

DEFAULT_PROFILE = {
    "personal": {
        "full_name": "", "email": "", "phone": "", "location": "",
        "website": "", "linkedin": "", "github": ""
    },
    "summary": "",
    "skills": [],
    "languages": ["English"],
    "links": []
}

@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def edit_profile():
    profile = current_user.get_profile() or DEFAULT_PROFILE
    if request.method == "POST":
        profile["personal"]["full_name"] = request.form.get("full_name","")
        profile["personal"]["email"] = request.form.get("p_email","")
        profile["personal"]["phone"] = request.form.get("phone","")
        profile["personal"]["location"] = request.form.get("location","")
        profile["personal"]["website"] = request.form.get("website","")
        profile["personal"]["linkedin"] = request.form.get("linkedin","")
        profile["personal"]["github"] = request.form.get("github","")
        profile["summary"] = request.form.get("summary","")
        profile["skills"] = [s.strip() for s in request.form.get("skills","").split(",") if s.strip()]
        profile["languages"] = [s.strip() for s in request.form.get("languages","").split(",") if s.strip()]
        current_user.save_profile(profile)
        flash("Profile saved", "success")
        return redirect(url_for("profile.edit_profile"))
    return render_template("profile.html", profile=profile)
