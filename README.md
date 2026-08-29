# Job Market Intelligence

An end-to-end resume-to-job matching application that analyzes a candidate's PDF resume, extracts technical skills, compares it against job descriptions, and ranks jobs using TF-IDF and cosine similarity.

The project combines **NLP-based text similarity, skill-gap analysis, PostgreSQL-backed job data, and a FastAPI backend** to help users understand both *which jobs match their profile* and *which skills they are missing*.

---

## Why this project?

Most job platforms return listings based on keywords or filters. This project explores a more candidate-centric workflow:

1. Upload a resume as a PDF.
2. Extract the resume text.
3. Identify technical skills from the resume.
4. Compare the resume with job descriptions using TF-IDF vectorization.
5. Rank jobs by cosine similarity.
6. Show matched and missing skills for each role.

The goal is not just to return jobs, but to make the match **interpretable**.

---

## Core Features

- **PDF resume parsing** using `PyPDF2`
- **Skill extraction** from resume and job descriptions
- **TF-IDF vectorization** for resume/job text representation
- **Cosine similarity** for job-match ranking
- **Skill-gap analysis** showing missing skills per job
- **PostgreSQL integration** for job storage and retrieval
- **FastAPI backend** for resume upload and scoring
- **Ranked job recommendations** sorted by resume similarity
- **API test coverage** for the backend workflow

---

## System Workflow

```text
                Resume PDF
                    |
                    v
             PDF Text Extraction
                    |
                    v
              Skill Extraction
                    |
                    +--------------------+
                    |                    |
                    v                    v
             Resume Skills        Resume Text
                                         |
                                         |
                         PostgreSQL Job Listings
                                         |
                                         v
                              Job Description Text
                                         |
                                         v
                              TF-IDF Vectorization
                                         |
                                         v
                               Cosine Similarity
                                         |
                    +--------------------+--------------------+
                    |                                         |
                    v                                         v
              Match Score                              Skill Comparison
                                                               |
                                                               v
                                                   Matched / Missing Skills
                    \                                         /
                     \                                       /
                      +-------------------------------------+
                                      |
                                      v
                              Ranked Job Results
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| Language | Python |
| Database | PostgreSQL |
| NLP / Matching | scikit-learn |
| Vectorization | TF-IDF |
| Similarity | Cosine Similarity |
| PDF Processing | PyPDF2 |
| Database Driver | psycopg2 |
| Configuration | python-dotenv |

---

## Matching Approach

### 1. Resume Parsing

The uploaded PDF is converted into lowercase text using `PyPDF2`.

### 2. Skill Extraction

The application compares the parsed text against a curated technical skill vocabulary.

Example skills include:

```text
Python, SQL, Machine Learning, Deep Learning,
FastAPI, Pandas, NumPy, AWS, Docker,
Kubernetes, Spark, Hadoop
```

### 3. Text Similarity

For every job description, the application creates TF-IDF vectors for:

```text
resume text
job description
```

It then calculates:

```text
cosine_similarity(resume_vector, job_vector)
```

The resulting score represents textual similarity between the candidate's resume and the role.

### 4. Skill-Gap Analysis

For each job:

```text
matched_skills = resume_skills ∩ job_skills
missing_skills = job_skills - resume_skills
```

This provides a simple explanation for why a role does or does not match the candidate.

---

## API

### `POST /upload-resume`

Uploads a PDF resume and returns jobs ranked by similarity.

Example response:

```json
{
  "jobs": [
    {
      "id": 12,
      "title": "Data Analyst",
      "company": "Example Corp",
      "location": "Bengaluru",
      "match_score": 0.61,
      "skill_score": 0.57,
      "skills": ["python", "sql", "pandas"],
      "missing_skills": ["spark"]
    }
  ]
}
```

> Note: the current implementation also contains an experimental `improved_score` field. It is a prototype value and should not be interpreted as a learned or production-grade ranking metric.

---

## Project Structure

```text
job-market-intel/
├── main.py              # FastAPI application and matching pipeline
├── skills.py            # Curated technical skill vocabulary
├── test_api.py          # API tests
├── index.html           # Front-end interface
├── requirements.txt     # Python dependencies
├── runtime.txt          # Runtime configuration
├── readme.txt           # Legacy run instructions
└── .gitignore
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/MohnishOnGitHub/job-market-intel.git
cd job-market-intel
```

### 2. Create a virtual environment

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure PostgreSQL

Create a `.env` file:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/job_market
```

The database should contain a `jobs` table with at least:

```sql
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    title TEXT,
    company TEXT,
    location TEXT,
    description TEXT
);
```

### 5. Run the API

```bash
uvicorn main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

FastAPI documentation:

```text
http://127.0.0.1:8000/docs
```

---

## Example Use Case

Suppose a resume contains:

```text
Python
SQL
Pandas
Machine Learning
FastAPI
```

and a Data Engineer role requires:

```text
Python
SQL
Spark
AWS
Docker
```

The system can identify:

```text
Matched:
Python
SQL

Missing:
Spark
AWS
Docker
```

while independently calculating a TF-IDF similarity score using the complete resume and job-description text.

This makes the recommendation more interpretable than a single unexplained score.

---

## Current Limitations

This repository represents an early version of the system.

Current limitations include:

- Skill extraction uses dictionary matching rather than entity recognition.
- TF-IDF does not capture semantic similarity between differently worded concepts.
- Job retrieval currently scores every stored job rather than using a retrieval stage.
- Skill importance is not weighted by role or seniority.
- PDF extraction depends on selectable PDF text.
- Ranking has not yet been evaluated against a labeled relevance dataset.
- The current experimental `improved_score` is heuristic rather than model-derived.

Documenting these limitations is intentional: they define the path toward a stronger production-grade matching system.

---

## Future Improvements

### Semantic Retrieval

Replace or complement TF-IDF with sentence/document embeddings.

Potential architecture:

```text
Resume
   |
Embedding Model
   |
   v
Vector Search
   |
Candidate Jobs
   |
Reranker
   |
Final Ranking
```

### Better Skill Extraction

Move from direct substring matching toward:

- NLP entity extraction
- skill normalization
- aliases and synonyms
- taxonomy-based matching

For example:

```text
Postgres -> PostgreSQL
sklearn  -> scikit-learn
ML       -> Machine Learning
```

### Hybrid Ranking

Combine:

- semantic similarity
- skill overlap
- experience level
- location preferences
- job-title similarity

### Evaluation

Create a labeled resume/job relevance dataset and measure:

- Precision@K
- Recall@K
- NDCG
- Mean Reciprocal Rank

### Production Engineering

Potential additions:

- Docker
- CI/CD
- database migrations
- structured logging
- validation
- caching
- vector database / pgvector
- deployment monitoring

---

## What I Learned

This project was built to explore several practical problems in data science and backend engineering:

- converting unstructured resume data into usable features
- comparing documents using TF-IDF
- ranking results using cosine similarity
- identifying explainable skill gaps
- serving an NLP workflow through FastAPI
- connecting application logic to PostgreSQL data

It also highlighted an important limitation of traditional lexical matching: two documents can be semantically similar even when they use different terminology. That naturally motivates the next stage of the system—embedding-based retrieval and more robust ranking.

---

## Author

**Mohnish Gurramkonda**

GitHub: [MohnishOnGitHub](https://github.com/MohnishOnGitHub)
