from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from dotenv import load_dotenv
from skills import SKILLS
from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os

# Load env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Safety check
if not DATABASE_URL:
    raise Exception("DATABASE_URL not set")

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB connection function
def get_connection():
    return psycopg2.connect(DATABASE_URL)


# Extract text from PDF
def extract_text(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text()
    return text.lower()


# Extract skills from resume
def extract_skills(text):
    found = []
    for skill in SKILLS:
        if skill in text:
            found.append(skill)
    return found


# Calculate match
def calculate_match(resume_text, job_text):
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([resume_text, job_text])
    score = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
    return round(score, 2)


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    try:
        # Read PDF
        contents = await file.read()
        with open("temp.pdf", "wb") as f:
            f.write(contents)

        resume_text = extract_text("temp.pdf")
        resume_skills = extract_skills(resume_text)

        # DB fetch
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, title, company, location, description FROM jobs")
        jobs = cursor.fetchall()

        results = []

        for job in jobs:
            job_id, title, company, location, description = job

            job_text = description.lower()

            match_score = calculate_match(resume_text, job_text)

            # Skill match
            job_skills = extract_skills(job_text)
            matched_skills = list(set(resume_skills) & set(job_skills))
            missing_skills = list(set(job_skills) - set(resume_skills))

            skill_score = len(matched_skills) / (len(job_skills) + 1)

            # Simulated improved score
            improved_score = round(min(match_score + 0.15, 1), 2)

            results.append({
                "id": job_id,
                "title": title,
                "company": company,
                "location": location,
                "match_score": match_score,
                "skill_score": round(skill_score, 2),
                "skills": job_skills,
                "missing_skills": missing_skills,
                "improved_score": improved_score
            })

        cursor.close()
        conn.close()

        # Sort best first
        results = sorted(results, key=lambda x: x["match_score"], reverse=True)

        return {"jobs": results}

    except Exception as e:
        return {"error": str(e)}