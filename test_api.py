import requests
import os
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("APP_ID")
APP_KEY = os.getenv("APP_KEY")

url = "https://api.adzuna.com/v1/api/jobs/in/search/1"

params = {
    "app_id": APP_ID,
    "app_key": APP_KEY,
    "results_per_page": 5,
    "what": "python developer",
    "where": "bangalore"
}

response = requests.get(url, params=params)

print("Status:", response.status_code)

data = response.json()

for job in data.get("results", []):
    print(job.get("title"))
    print(job.get("company", {}).get("display_name"))
    print(job.get("location", {}).get("display_name"))
    print("-" * 40)