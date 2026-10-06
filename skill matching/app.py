import os
import subprocess
import requests
import secrets
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Necessary for using `session`
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Dictionary to map datasets
DATA_FILES = {
    '1': ('data/data_1.csv', 'data/data_11.csv'),
    '2': ('data/data_2.csv', 'data/data_21.csv'),
    '3': ('data/data_3.csv', 'data/data_31.csv'),
    '4': ('data/data_4.csv', 'data/data_41.csv'),
    '5': ('data/data_5.csv', 'data/data_51.csv'),
    '6': ('data/data_6.csv', 'data/data_61.csv'),
    '7': ('data/data_7.csv', 'data/data_71.csv'),
    '8': ('data/data_8.csv', 'data/data_81.csv')
}

# Global variables
job_df = None
trending_df = None
vectorizer = None
model = None


# Function to load and preprocess datasets
def load_datasets(dataset_id):
    global job_df, trending_df, vectorizer, model
    job_path, trending_path = DATA_FILES[dataset_id]
    job_path = os.path.join(BASE_DIR, job_path)
    trending_path = os.path.join(BASE_DIR, trending_path)
    job_df = pd.read_csv(job_path)
    trending_df = pd.read_csv(trending_path)

    # Merge and preprocess data
    job_df = pd.merge(job_df, trending_df, on="JobTitle", how="left")
    job_df["TrendingScore"] = job_df["TrendingScore"].fillna(0).astype(float)
    job_df['CombinedSkills'] = job_df[['TechnicalSkills', 'Frameworks', 'VersionControl', 'SoftSkills', 'Tools']].fillna('').agg(', '.join, axis=1)

    # Determine median for top jobs
    median_trending_score = job_df["TrendingScore"].median()
    job_df["IsTopJob"] = (job_df["TrendingScore"] > median_trending_score).astype(int)

    # Train model
    X = job_df["CombinedSkills"]
    y = job_df["IsTopJob"]
    vectorizer = CountVectorizer()
    X_vectorized = vectorizer.fit_transform(X)
    model = LogisticRegression()
    model.fit(X_vectorized, y)


# Function to recommend jobs
def recommend_jobs(user_input):
    user_skills_set = set(skill.strip().lower() for skill in user_input.split(','))

    job_df["MatchedSkillsCount"] = job_df["CombinedSkills"].apply(
        lambda skills: len(user_skills_set.intersection(set(skill.strip().lower() for skill in skills.split(','))))
    )
    job_df["MissingSkills"] = job_df["CombinedSkills"].apply(
        lambda skills: ', '.join(set(skill.strip().lower() for skill in skills.split(',')) - user_skills_set) or "None"
    )

    perfect_match_jobs = job_df[job_df["MissingSkills"] == "None"]

    if not perfect_match_jobs.empty:
        perfect_match_jobs = perfect_match_jobs.sort_values(by="TrendingScore", ascending=False)
        return perfect_match_jobs.head(3)[["JobTitle", "TrendingScore", "MissingSkills"]].to_dict('records')

    job_df["PredictedTopJobProbability"] = model.predict_proba(vectorizer.transform(job_df["CombinedSkills"]))[:, 1]
    job_df["Score"] = job_df["MatchedSkillsCount"] + (job_df["TrendingScore"] * 0.5) + (job_df["PredictedTopJobProbability"] * 2)

    top_jobs = job_df.sort_values(by="Score", ascending=False).head(3)

    recommendations = []
    for _, row in top_jobs.iterrows():
        recommendations.append({
            "JobTitle": row["JobTitle"],
            "TrendingScore": row["TrendingScore"],
            "MissingSkills": row["MissingSkills"],
            "Score": row["Score"]
        })
    return recommendations

@app.route('/')
def home():
    return render_template('home.html')


# Routes for switching dataset
@app.route('/switch_dataset')
def switch_dataset():
    dataset_id = request.args.get('dataset')
    selected_domain = request.args.get('selected_domain', 'None')
    if dataset_id in DATA_FILES:
        load_datasets(dataset_id)
        session['current_dataset'] = dataset_id  # Save dataset ID in session
        return redirect(url_for('index', selected_domain=selected_domain))
    else:
        return "Dataset not found", 404
    
# Routes for different domains
@app.route('/Aerospace')
def aerospace():
    return render_template('1.html')

@app.route('/Artificial Intelligence')
def artificial_intelligence():
    return render_template('2.html')

@app.route('/Biomedical')
def biomedical():
    return render_template('3.html')

@app.route('/Chemical')
def chemical():
    return render_template('4.html')

@app.route('/Civil')
def civil():
    return render_template('5.html')

@app.route('/Mechanical')
def mechanical():
    return render_template('6.html')

@app.route('/Electronics and Communication')
def electronics_communication():
    return render_template('7.html')

@app.route('/Computer Science')
def computer_science():
    return render_template('8.html')

@app.route('/index', methods=['GET', 'POST'])
def index():
    selected_domain = request.args.get('selected_domain', 'None')
    if request.method == 'POST':
        skills = request.form.get('skills')
        return redirect(url_for('recommendations', skills=skills, selected_domain=selected_domain))
    return render_template('index.html', selected_domain=selected_domain)


@app.route('/recommendations')
def recommendations():
    skills = request.args.get('skills', '')
    recommendations = recommend_jobs(skills)
    return render_template('recommendations.html', recommendations=recommendations)


@app.route('/details/<job_title>')
def details(job_title):
    job = job_df[job_df['JobTitle'] == job_title].iloc[0]
    missing_skills = job['MissingSkills']
    return render_template('details.html', job_title=job_title, missing_skills=missing_skills)


# ✅ Automatically Start Flask Server When Opening `home.html`
def start_server():
    subprocess.Popen(["python", "app.py"])

@app.route('/check_server')
def check_server():
    try:
        requests.get("http://127.0.0.1:5000")
        return jsonify({"status": "running"})
    except:
        return jsonify({"status": "stopped"}), 500

@app.route('/start_server')
def start_flask_server():
    start_server()
    return jsonify({"status": "starting"})


if __name__ == '__main__':
    load_datasets('5')  # Load default dataset
    app.run(debug=True, host='0.0.0.0', port=5000)
