from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from dotenv import load_dotenv
from skills import SKILLS
from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

app = FastAPI()

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔌 DB connection
def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="job_market",
        user="postgres",
        password="Mohnish@2006"
    )

# 🧠 Skill extraction
def extract_skills(text: str):
    if not text:
        return []
    text = text.lower()
    return list(set([skill for skill in SKILLS if skill in text]))

# 📄 PDF reader
def extract_text_from_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# 🧠 Skill match
def skill_match_score(user_skills, job_skills):
    if not user_skills:
        return 0
    matches = 0
    for us in user_skills:
        for js in job_skills:
            if us in js or js in us:
                matches += 1
                break
    return matches / len(user_skills)

# 🚀 MAIN API
@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):

    resume_text = extract_text_from_pdf(file.file)
    user_skills = extract_skills(resume_text)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT title, company, location, description, created_at FROM jobs")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    job_descriptions = [row[3] for row in rows]
    corpus = [resume_text] + job_descriptions

    vectorizer = TfidfVectorizer(stop_words="english")
    vectors = vectorizer.fit_transform(corpus)

    similarity_scores = cosine_similarity(vectors[0:1], vectors[1:]).flatten()

    result = []

    for i, row in enumerate(rows):
        job_skills = extract_skills(row[3])

        # 🔥 FIXED missing skills logic
        missing_skills = []
        for js in job_skills:
            found = False
            for us in user_skills:
                if js in us or us in js:
                    found = True
                    break
            if not found:
                missing_skills.append(js)

        tfidf_score = float(similarity_scores[i])
        skill_score = skill_match_score(user_skills, job_skills)

        # 🎯 current score
        final_score = (0.5 * tfidf_score) + (0.5 * skill_score)
        if skill_score == 1:
            final_score += 0.1

        # 🔮 projected score
        future_user_skills = user_skills + missing_skills[:3]
        future_skill_score = skill_match_score(future_user_skills, job_skills)

        projected_score = (0.5 * tfidf_score) + (0.5 * future_skill_score)
        if future_skill_score == 1:
            projected_score += 0.1

        result.append({
            "title": row[0],
            "company": row[1],
            "location": row[2],
            "skills": job_skills,
            "missing_skills": missing_skills[:3],
            "match_score": round(final_score, 2),
            "projected_score": round(projected_score, 2),
            "tfidf_score": round(tfidf_score, 2),
            "skill_score": round(skill_score, 2),
            "created_at": row[4]
        })

    result.sort(key=lambda x: x["match_score"], reverse=True)
    result = result[:5]

    return {
        "extracted_skills": user_skills,
        "jobs": result
    }