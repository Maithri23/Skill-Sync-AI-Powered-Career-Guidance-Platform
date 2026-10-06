from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import os
import speech_recognition as sr
import pandas as pd
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import re
import json
import time

# ===== NEW: Groq API Import =====
from groq import Groq

# === Extra imports for video evaluation ===
# Video analysis dependencies are imported only when a video answer is sent.
# Loading Whisper here made the complete Interview Practice page unavailable
# whenever its model cache had not been created yet.

# ----------------- CONFIG -----------------
app = Flask(__name__)
app.secret_key = 'my_super_secret_key_456789'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ===== Groq API Configuration =====
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

model_whisper = None


def get_whisper_model():
    """Load the video transcription model only for a video submission."""
    global model_whisper
    if model_whisper is None:
        import whisper
        model_whisper = whisper.load_model("small")
    return model_whisper

# ===== NEW: Helper Function for Groq API with Error Handling =====
def call_groq_api(prompt, max_retries=3):
    """
    Calls Groq API with retry logic and error handling
    """
    if groq_client is None:
        return None

    for attempt in range(max_retries):
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Best free model for quality
                messages=[
                    {"role": "system", "content": "You are an expert interview assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2048
            )
            return response.choices[0].message.content
        
        except Exception as e:
            print(f"Groq API Error (Attempt {attempt + 1}/{max_retries}): {str(e)}")
            
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                # Final fallback response
                return json.dumps({
                    "error": "API temporarily unavailable. Please try again.",
                    "status": "failed"
                })
    
    return None

# ============================================================
# ===== Utility Functions (Audio Interview Part) =============
# ============================================================

def SpeechToText():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("Adjusting for ambient noise...")
            r.adjust_for_ambient_noise(source)
            print("Listening...")
            audio = r.listen(source)
        print("Recognizing...")
        query = r.recognize_google(audio, language='en-IN')
        return query
    except sr.UnknownValueError:
        return "Could not understand the audio."
    except sr.RequestError as e:
        return f"Could not request results from Google Speech Recognition service; {e}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

def clean_answer(answer):
    words = word_tokenize(answer)
    stop_words = set(stopwords.words('english'))
    return ' '.join([word for word in words if word.lower() not in stop_words])

# ============================================================
# ===== Routes for Main Project (Groq-based) =================
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_questions', methods=['POST'])
def generate_questions():
    job = request.form['job']
    level = request.form['level']
    session['job_title'] = job
    session['difficulty'] = level
    return redirect(url_for('regenerate_questions'))

@app.route('/regenerate_questions')
def regenerate_questions():
    job = session.get('job_title')
    level = session.get('difficulty')

    # ✅ Generate fresh questions using Groq API
    prompt = f"""
    Generate exactly 10 interview questions for the job role: {job} 
    with difficulty level: {level}. 
    Only return the 10 questions in plain text, numbered 1 to 10. 
    Do not include any introduction or extra comments.
    """
    
    response_text = call_groq_api(prompt)
    
    if not response_text or "error" in response_text.lower():
        # Fallback questions if API fails
        questions = [
            f"Tell me about your experience in {job}.",
            f"What are your key strengths for this {job} role?",
            f"Describe a challenging project you worked on.",
            f"How do you handle tight deadlines?",
            f"What motivates you in your career?",
            f"Where do you see yourself in 5 years?",
            f"How do you stay updated with industry trends?",
            f"Describe your ideal work environment.",
            f"What is your greatest professional achievement?",
            f"Why are you interested in this {job} position?"
        ]
    else:
        # ✅ Extract only the question texts
        raw_questions = response_text.strip().split("\n")
        questions = []
        for q in raw_questions:
            question = re.sub(r'^\s*(?:\d+[\).:\-]?|[-*â€¢])\s*', '', q).strip()
            if question and not question.lower().startswith(("here are", "interview questions")):
                questions.append(question)

        questions = questions[:10]  # ✅ Ensure only 10
    
    session['questions'] = questions  # ✅ Save fresh set
    if len(questions) < 10:
        questions = [
            f"Tell me about your experience in {job}.",
            f"What are your key strengths for this {job} role?",
            "Describe a challenging project you worked on.",
            "How do you handle tight deadlines?",
            "What motivates you in your career?",
            "Where do you see yourself in 5 years?",
            "How do you stay updated with industry trends?",
            "Describe your ideal work environment.",
            "What is your greatest professional achievement?",
            f"Why are you interested in this {job} position?"
        ]
        session['questions'] = questions

    return redirect(url_for('questions'))

@app.route('/questions')
def questions():
    questions = session.get('questions', [])
    job = session.get('job_title')
    difficulty = session.get('difficulty')
    question_list = list(enumerate(questions, start=1))
    return render_template('questions.html', questions=question_list, job_title=job, difficulty=difficulty)

@app.route('/interview/<int:qid>')
def interview(qid):
    questions = session.get('questions', [])
    if 1 <= qid <= len(questions):
        question = questions[qid - 1]
    else:
        question = 'No question found'
    return render_template('interview.html', question=question, qid=qid)

@app.route('/get_analysis', methods=['POST'])
def get_analysis():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file"}), 400

    audio_file = request.files['audio']
    audio_path = os.path.join(BASE_DIR, "user_audio.wav")
    audio_file.save(audio_path)

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
        transcribed_text = recognizer.recognize_google(audio)
        duration = 10
    except sr.UnknownValueError:
        return jsonify({"error": "Could not understand audio."}), 400
    except sr.RequestError as e:
        return jsonify({"error": f"Speech recognition failed: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

    return jsonify({
        "transcription": transcribed_text,
        "duration": duration
    })

@app.route('/submit_answer/<qid>', methods=['POST'])
def submit_answer(qid):
    user_answer = request.form.get('answer', '').strip()

    prompt = f"""
    You are an expert interviewer. Analyze the user's answer concisely in JSON:

    {{
        "correct_answer": "Ideal answer",
        "validation": "Valid/Invalid/Partial",
        "feedback": "Brief feedback"
    }}

    Question ID: {qid}
    User Answer: "{user_answer}"
    """
    
    response_text = call_groq_api(prompt)
    
    try:
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            result = json.loads(json_str)
        else:
            raise ValueError("No JSON object found")
    except Exception:
        result = {
            "correct_answer": "Unable to parse response.",
            "validation": "Unknown",
            "feedback": "N/A"
        }

    return jsonify({
        'user_answer': user_answer,
        'validation_result': {
            'correct_answer': result.get('correct_answer', ''),
            'validation': result.get('validation', ''),
            'feedback': result.get('feedback', '')
        },
    })

# ============================================================
# ===== Video Interview Routes ===============================
# ============================================================

@app.route('/video_interview')
def video_interview():
    return render_template('video_interview.html')

@app.route('/submit_video_answer/<qid>', methods=['POST'])
def submit_video_answer(qid):
    if 'video' not in request.files:
        return jsonify({"error": "No video uploaded"}), 400

    file = request.files['video']
    uploads_dir = os.path.join(BASE_DIR, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    filepath = os.path.join(uploads_dir, f"answer_{qid}.webm")
    file.save(filepath)

    # Step 1: Transcribe user's speech using Whisper
    result = get_whisper_model().transcribe(filepath)
    transcript = result['text']

    # Step 2: Ask Groq API to analyze and give scores + feedback
    prompt = f"""
    You are an expert interview evaluator.
    Analyze this interview answer for question ID {qid} and return JSON in this exact format:
    {{
        "Confidence Score": <float between 0 and 1>,
        "Content Relevance": <float between 0 and 1>,
        "Fluency Score": <float between 0 and 1>,
        "Feedback": "3–5 line constructive feedback on how the user can improve"
    }}

    User's answer transcript: "{transcript}"
    """

    response_text = call_groq_api(prompt)
    
    try:
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

        if json_match:
            json_str = json_match.group()
            scores = json.loads(json_str)
        else:
            # Fallback if parsing fails
            scores = {
                "Confidence Score": 0.5,
                "Content Relevance": 0.5,
                "Fluency Score": 0.5,
                "Feedback": "Unable to analyze answer properly."
            }
    except Exception:
        scores = {
            "Confidence Score": 0.5,
            "Content Relevance": 0.5,
            "Fluency Score": 0.5,
            "Feedback": "AI evaluation failed due to a technical issue."
        }

    # Step 3: Compute final evaluation
    try:
        final_eval = round(
            (scores["Confidence Score"] +
             scores["Content Relevance"] +
             scores["Fluency Score"]) / 3 * 100, 2
        )
    except Exception:
        final_eval = 50.0

    # ✅ Step 4: Save feedback for result page
    session['video_feedback'] = scores["Feedback"]

    # Step 5: Send back to frontend
    return jsonify({
        "Confidence Score": scores["Confidence Score"],
        "Content Relevance": scores["Content Relevance"],
        "Fluency Score": scores["Fluency Score"],
        "Final Evaluation": final_eval,
        "Transcript": transcript,
        "Feedback": scores["Feedback"]
    })

# ============================================================
# ===== Result Page ==========================================
# ============================================================

@app.route('/result')
def result():
    feedback = session.get('video_feedback', "No feedback available yet.")
    return render_template('result.html', feedback=feedback)

# ============================================================

if __name__ == '__main__':
    app.run(debug=True)
