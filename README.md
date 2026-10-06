# SkillSync — AI-Powered Career Guidance Platform

SkillSync is a unified Flask application that brings four career-development
tools together behind one dashboard.

## Features

- **Resume Builder:** Build resumes, cover letters, professional profiles, and
  track job applications.
- **Skill Matching:** Receive job recommendations based on selected domain and
  skills.
- **Interview Practice:** Generate interview questions and receive AI feedback
  for text, speech, or video answers.
- **Resume Evaluator:** Evaluate a resume against a job description, calculate
  a match score, and create an improved DOCX version.

## Project structure

```text
app.py                 # Unified Flask launcher
resume builder/        # Resume builder feature
skill matching/        # Skill-based job matching feature
Interview-SKILLSYNC/   # Interview practice feature
Resume Evaluater/      # Resume evaluation feature
```

## Setup

1. Clone the repository and enter the project folder.
2. Create and activate a virtual environment.
3. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and provide the API keys required for the AI
   features. Never commit `.env`.
5. Start the application:

   ```powershell
   python app.py
   ```

6. Open <http://127.0.0.1:5000>.

## Configuration

| Variable | Used by | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | Interview Practice | Generates questions and answer feedback. |
| `GEMINI_API_KEY` | Resume Evaluator | Evaluates and improves resumes. |
| `SECRET_KEY` | Resume Builder | Secures Flask sessions. |

Without an active Groq key, Interview Practice still supplies its built-in
fallback questions. Video transcription may require Whisper model files; OCR
may require locally installed Tesseract and Poppler.

## Run routes

| Route | Tool |
| --- | --- |
| `/` | SkillSync dashboard |
| `/resumes/` | Resume Builder |
| `/skills/` | Skill Matching |
| `/interview/` | Interview Practice |
| `/evaluate/` | Resume Evaluator |

## Security

API keys, uploaded interview videos, local databases, model files, and other
generated data are intentionally excluded from version control through
`.gitignore`.
