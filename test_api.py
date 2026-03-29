import requests
import os
from dotenv import load_dotenv
import psycopg2

# Load env variables
load_dotenv()

APP_ID = os.getenv("APP_ID")
APP_KEY = os.getenv("APP_KEY")

# 🔥 Connect to PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    database="job_market",
    user="postgres",
    password="Mohnish@2006"  # <-- replace this
)

cur = conn.cursor()

# API params
params = {
    "app_id": APP_ID,
    "app_key": APP_KEY,
    "results_per_page": 5,
    "what": "python developer",
    "where": "bangalore"
}


# Parse job data
def parse_job(job):
    return {
        "title": job.get("title"),
        "company": job.get("company", {}).get("display_name"),
        "location": job.get("location", {}).get("display_name"),
        "description": job.get("description"),
        "created_at": job.get("created")
    }


# Fetch + insert data
for page in range(1, 4):
    url = f"https://api.adzuna.com/v1/api/jobs/in/search/{page}"

    response = requests.get(url, params=params)
    print(f"Page {page} Status:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        continue

    data = response.json()

    for job in data.get("results", []):
        parsed = parse_job(job)

        cur.execute(
            """
            INSERT INTO jobs (title, company, location, description, created_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                parsed["title"],
                parsed["company"],
                parsed["location"],
                parsed["description"],
                parsed["created_at"]
            )
        )


# Save changes
conn.commit()

# Close connection
cur.close()
conn.close()

print("✅ Data inserted (no duplicates)")