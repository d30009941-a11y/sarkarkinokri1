import os
import json
import re
import time
import pdfplumber
from datetime import datetime
from google import genai

# ==========================
# CONFIGURATION
# ==========================
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
)

PDF_DIR = "notification/"
JOBS_DIR = "data/jobsdata/"
EVENTS_FILE = "data/events.json"


# ==========================
# SAFE JSON LOADER
# ==========================
def load_events():
    if not os.path.exists(EVENTS_FILE):
        return {"data": []}

    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)

    if "data" not in db or not isinstance(db["data"], list):
        db["data"] = []

    return db


# ==========================
# PDF TEXT EXTRACTION
# ==========================
def extract_pdf_text(path):
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:10]:
                content = page.extract_text()
                if content:
                    text += content + "\n"
    except Exception as e:
        print("PDF extraction error:", e)

    return text


# ==========================
# AI EXTRACTION WITH RETRY
# ==========================
def extract_structured_data(slug_id, text):

    prompt = f"""
Return ONLY valid JSON.

Root key must be exactly "{slug_id}"

Extract structured recruitment data from this notification text:

{text[:12000]}
"""

    max_retries = 5
    wait_time = 5  # initial wait time (seconds)

    for attempt in range(max_retries):
        try:
            print(f"🤖 AI Attempt {attempt+1}")

            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=prompt
            )

            response_text = response.text

            match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if not match:
                raise ValueError("AI did not return valid JSON")

            return json.loads(match.group(0))

        except Exception as e:
            print(f"⚠ Attempt {attempt+1} failed: {e}")

            if attempt < max_retries - 1:
                print(f"⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                wait_time *= 2  # exponential backoff
            else:
                raise e


# ==========================
# SCHEMA ENFORCER
# ==========================
def enforce_schema(slug_id, data):
    base = data.get(slug_id, {})

    def ensure(obj, key, default):
        if key not in obj or obj[key] is None:
            obj[key] = default

    ensure(base, "overview", {})
    ensure(base, "important_dates", {})
    ensure(base, "application_fee", {})
    ensure(base, "age_limit", {"minimum": "", "maximum": "", "relaxation": ""})
    ensure(base, "educational_qualification", [])
    ensure(base, "vacancy_details", {"total": "", "table": []})
    ensure(base, "selection_process", [])
    ensure(base, "syllabus", {"mathematics": [], "reasoning": [], "general_awareness": []})
    ensure(base, "medical_standards", {})
    ensure(base, "important_instructions", [])
    ensure(base, "important_links", {"links": {}})

    if "links" not in base["important_links"]:
        base["important_links"]["links"] = {}

    data[slug_id] = base
    return data


# ==========================
# SAVE JOB JSON
# ==========================
def save_job_json(slug_id, data):
    os.makedirs(JOBS_DIR, exist_ok=True)

    with open(f"{JOBS_DIR}{slug_id}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# ==========================
# UPDATE EVENTS.JSON
# ==========================
def update_events(slug_id, structured_data):
    db = load_events()
    existing_ids = {item["id"] for item in db["data"]}

    if slug_id in existing_ids:
        print("⏩ Already exists in events.json")
        return

    base = structured_data[slug_id]

    meta_entry = {
        "id": slug_id,
        "master": base.get("overview", {}).get("post_name", slug_id),
        "lifecycle": "notification",
        "phase": "",
        "region": "",
        "notification_type": "detailed",
        "type": "Recruitment",
        "status": "Active",
        "url": base.get("important_links", {}).get("links", {}).get("Official Website", ""),
        "last_updated": datetime.now().strftime("%Y-%m-%d")
    }

    db["data"].insert(0, meta_entry)

    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)


# ==========================
# MAIN ENGINE
# ==========================
def run_engine():

    if not os.path.exists(PDF_DIR):
        print("❌ Notification folder not found.")
        return

    db = load_events()
    existing_ids = {item["id"] for item in db["data"]}

    for file in os.listdir(PDF_DIR):

        if not file.lower().endswith(".pdf"):
            continue

        slug_id = file.lower().replace(".pdf", "").replace(" ", "-")[:50]

        if slug_id in existing_ids:
            print(f"⏩ Skipped existing: {slug_id}")
            continue

        print(f"🚀 Processing: {file}")

        text = extract_pdf_text(os.path.join(PDF_DIR, file))

        if not text.strip():
            print("❌ No extractable text found.")
            continue

        try:
            structured_data = extract_structured_data(slug_id, text)
            structured_data = enforce_schema(slug_id, structured_data)

            save_job_json(slug_id, structured_data)
            update_events(slug_id, structured_data)

            print(f"✅ Successfully saved: {slug_id}")

        except Exception as e:
            print(f"❌ Final failure in {file}: {e}")


if __name__ == "__main__":
    run_engine()