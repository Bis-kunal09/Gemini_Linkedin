import hashlib
import json
import os
import random
import re
import time
import requests
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

COMMON_SKILLS = [
    "Python", "Java", "C++", "C#", "Go", "Rust", "JavaScript", "TypeScript",
    "React", "Angular", "Vue", "Node.js", "FastAPI", "Django", "Flask",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis",
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "CI/CD",
    "Machine Learning", "PyTorch", "TensorFlow", "Pandas", "Spark"
]

def extract_skills_locally(text: str) -> list:
    return [s for s in COMMON_SKILLS if re.search(rf"\b{re.escape(s)}\b", text, re.IGNORECASE)]

def generate_id(title: str, company: str, loc: str) -> str:
    return hashlib.md5(f"{title}-{company}-{loc}".lower().encode()).hexdigest()[:10]

def scrape_linkedin(keyword: str, location: str = "Remote", max_pages: int = 2):
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    results = []

    for page in range(max_pages):
        params = {"keywords": keyword, "location": location, "start": page * 25}
        headers = {"User-Agent": random.choice(USER_AGENTS)}

        try:
            print(f"Scraping '{keyword}' in '{location}' (Page {page + 1})...")
            res = requests.get(base_url, params=params, headers=headers, timeout=10)
            if res.status_code != 200:
                break

            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.find_all("li")
            if not cards:
                break

            for card in cards:
                t = card.find("h3", class_="base-search-card__title")
                c = card.find("h4", class_="base-search-card__subtitle")
                l = card.find("span", class_="job-search-card__location")
                lnk = card.find("a", class_="base-card__full-link")
                d = card.find("time")

                if t and c:
                    title = t.get_text(strip=True)
                    company = c.get_text(strip=True)
                    loc_text = l.get_text(strip=True) if l else location
                    link = lnk["href"].split("?")[0] if lnk and "href" in lnk.attrs else ""
                    date = d.get_text(strip=True) if d else "Recent"

                    results.append({
                        "id": generate_id(title, company, loc_text),
                        "title": title,
                        "company": company,
                        "location": loc_text,
                        "link": link,
                        "date_posted": date,
                        "skills": extract_skills_locally(f"{title} {loc_text}"),
                        "description": f"{title} opportunity at {company} ({loc_text})."
                    })
            time.sleep(random.uniform(1.5, 3.0))
        except Exception as e:
            print(f"Error: {e}")
            break

    return results

def main():
    queries = [
        ("Software Engineer", "Remote"),
        ("Python Developer", "United States"),
        ("Data Scientist", "Remote"),
        ("Frontend Engineer", "Remote"),
        ("DevOps Engineer", "United States")
    ]
    job_store = {}

    if os.path.exists("jobs.json"):
        try:
            with open("jobs.json", "r", encoding="utf-8") as f:
                for j in json.load(f):
                    job_store[j["id"]] = j
        except Exception:
            pass

    for q, loc in queries:
        for job in scrape_linkedin(q, loc, max_pages=1):
            job_store[job["id"]] = job

    with open("jobs.json", "w", encoding="utf-8") as f:
        json.dump(list(job_store.values()), f, indent=2)

    print(f"Saved {len(job_store)} jobs to jobs.json")

if __name__ == "__main__":
    main()
