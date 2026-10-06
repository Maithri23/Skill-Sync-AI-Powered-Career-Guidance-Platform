"""SkillSync unified application launcher.

The original projects remain independent Flask applications.  This file mounts
them under one server so their routes, templates, and existing behaviour do
not conflict with one another.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from threading import Lock

from flask import Flask, render_template_string
from werkzeug.middleware.dispatcher import DispatcherMiddleware

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parent

if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env")


class LazyApplication:
    """Load a feature only when somebody opens it.

    Some feature folders use optional AI libraries.  Lazy loading means the
    dashboard and the other features remain available if one feature's
    optional dependencies have not yet been installed.
    """

    def __init__(self, module_name: str, folder: str):
        self.module_name = module_name
        self.folder = PROJECT_ROOT / folder
        self.application = None
        self.error = None
        self.lock = Lock()

    def _load(self):
        if self.application is not None or self.error is not None:
            return
        with self.lock:
            if self.application is not None or self.error is not None:
                return
            try:
                module_path = self.folder / "app.py"
                spec = importlib.util.spec_from_file_location(self.module_name, module_path)
                if spec is None or spec.loader is None:
                    raise ImportError(f"Could not load {module_path}")
                module = importlib.util.module_from_spec(spec)
                sys.modules[self.module_name] = module
                sys.path.insert(0, str(self.folder))
                try:
                    spec.loader.exec_module(module)
                finally:
                    sys.path.remove(str(self.folder))
                self.application = module.app
            except Exception as exc:  # Show setup guidance without breaking other tools.
                self.error = exc

    def __call__(self, environ, start_response):
        self._load()
        if self.application is not None:
            return self.application(environ, start_response)
        message = (
            "<h1>Feature setup required</h1>"
            "<p>This feature could not start because one of its Python "
            "dependencies is missing or misconfigured.</p>"
            "<p>Install the project requirements and restart the server.</p>"
        )
        start_response("503 Service Unavailable", [("Content-Type", "text/html; charset=utf-8")])
        return [message.encode("utf-8")]


hub = Flask(__name__)


@hub.route("/")
def home():
    return render_template_string(
        """<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">
        <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
        <title>SkillSync</title><style>
        *{box-sizing:border-box}body{margin:0;min-height:100vh;font-family:Arial,sans-serif;color:#fff;background:linear-gradient(135deg,#56d8ff,#457b9d,#a8dadc,#e63946);background-size:300% 300%;animation:gradient 15s ease infinite}
        @keyframes gradient{0%,100%{background-position:0 50%}50%{background-position:100% 50%}}
        header{text-align:center;padding:64px 20px 35px}h1{font-size:clamp(2.4rem,6vw,4.5rem);margin:0;text-shadow:2px 2px 10px rgba(0,0,0,.35)}header p{font-size:1.15rem;margin:13px 0 0;color:#f4f8ff}
        main{max-width:1120px;margin:0 auto;padding:22px 24px 70px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(225px,1fr));gap:22px}
        a{display:block;min-height:235px;padding:27px 25px;background:rgba(0,0,0,.74);border:2px solid #f39c12;border-radius:16px;color:#fff;text-decoration:none;box-shadow:0 10px 28px rgba(0,0,0,.32);transition:transform .25s,box-shadow .25s}a:hover{transform:translateY(-7px);box-shadow:0 17px 35px rgba(0,0,0,.45)}h2{font-size:1.65rem;margin:0 0 18px;color:#ffd166}p{line-height:1.6;margin:0;color:#fff}
        </style></head><body><header><h1>SkillSync</h1><p>Your career tools, connected in one place</p></header>
        <main><div class=\"grid\">
        <a href=\"/resumes/\"><h2>Resume Builder</h2><p>Create resumes, cover letters, profiles, and track applications.</p></a>
        <a href=\"/skills/\"><h2>Skill Matching</h2><p>Explore career domains and get job recommendations from your skills.</p></a>
        <a href=\"/interview/\"><h2>Interview Practice</h2><p>Generate interview questions and receive answer feedback.</p></a>
        <a href=\"/evaluate/\"><h2>Resume Evaluator</h2><p>Evaluate, match, and improve an uploaded resume.</p></a>
        </div></main></body></html>"""
    )


application = DispatcherMiddleware(
    hub,
    {
        "/resumes": LazyApplication("skillsync_resume_builder", "resume builder"),
        "/skills": LazyApplication("skillsync_skill_matching", "skill matching"),
        "/interview": LazyApplication("skillsync_interview", "Interview-SKILLSYNC"),
        "/evaluate": LazyApplication("skillsync_resume_evaluator", "Resume Evaluater"),
    },
)


if __name__ == "__main__":
    from werkzeug.serving import run_simple

    run_simple("127.0.0.1", 5000, application, use_reloader=True, use_debugger=True)
