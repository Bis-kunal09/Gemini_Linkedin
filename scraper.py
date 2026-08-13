import json
import logging
import os
from datetime import datetime;import re
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Target Job Title and Location
KEYWORDS = "Data Engineer"
LOCATION = "Noida"  # e.g., "United States", "India", "Remote"
DATA_FILE = "jobs.json"

# LinkedIn public job search endpoint
URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

def load_existing_jobs():
    """Load existing logged jobs to avoid duplicates."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.warning(f"Could not parse {DATA_FILE}, starting fresh.")
    return []

def save_jobs(jobs):
    """Save updated job list back to JSON file."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)

def fetch_jobs():
    """Fetch job listings from LinkedIn public endpoint."""
    params = {
        "keywords": KEYWORDS,
        "location": LOCATION,
        "start": 0,  # Page offset
        "f_TPR": "r86400"  # Jobs posted in the last 24 hours (86,400 seconds)
    }

    logging.info(f"Searching LinkedIn for '{KEYWORDS}' in '{LOCATION}'...")
    response = requests.get(URL, params=params, headers=HEADERS)

    if response.status_code != 200:
        logging.error(f"Failed to fetch jobs from LinkedIn. HTTP Status: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    job_cards = soup.find_all("li")
    
    scraped_jobs = []

    for card in job_cards:
        try:
            title_tag = card.find("h3", class_="base-search-card__title")
            company_tag = card.find("h4", class_="base-search-card__subtitle")
            location_tag = card.find("span", class_="job-search-card__location")
            link_tag = card.find("a", class_="base-card__full-link")
            time_tag = card.find("time")

            if not (title_tag and link_tag):
                continue

            title = title_tag.text.strip()
            company = company_tag.text.strip() if company_tag else "Unknown"
            location = location_tag.text.strip() if location_tag else "N/A"
            link = link_tag["href"].split("?")[0]  # Clean tracking parameters from URL
            posted_date = time_tag["datetime"] if time_tag and time_tag.has_attr("datetime") else datetime.utcnow().strftime("%Y-%m-%d")

            # Extract LinkedIn Job ID from URL
            job_id_match = re.search(r"-(\d+)$", link)
            job_id = job_id_match.group(1) if job_id_match else link

            scraped_jobs.append({
                "job_id": job_id,
                "title": title,
                "company": company,
                "location": location,
                "link": link,
                "posted_date": posted_date,
                "scraped_at": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logging.debug(f"Error parsing job card: {e}")
            continue

    return scraped_jobs

def main():
    existing_jobs = load_existing_jobs()
    existing_ids = {job["job_id"] for job in existing_jobs}

    new_jobs = fetch_jobs()
    added_count = 0

    for job in new_jobs:
        if job["job_id"] not in existing_ids:
            logging.info(f"✨ NEW JOB FOUND: {job['title']} at {job['company']} ({job['location']})")
            existing_jobs.insert(0, job)  # Prepend newest jobs
            existing_ids.add(job["job_id"])
            added_count += 1

    if added_count > 0:
        logging.info(f"Successfully logged {added_count} new job postings.")
        save_jobs(existing_jobs)
    else:
        logging.info("No new Data Engineer job postings found since last check.")

if __name__ == "__main__":
    main()
