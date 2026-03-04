import os

print("Current working directory:", os.getcwd())
print("Folders in root:", os.listdir())
print("Notification folder exists:", os.path.exists("notification"))
print("Files inside notification:", os.listdir("notification") if os.path.exists("notification") else "NOT FOUND")
import os
import json
import re
import pdfplumber
import google.generativeai as genai
from datetime import datetime

# ==========================
# CONFIGURATION
# ==========================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

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

    # Self-healing structure
    if "data" not in db or not isinstance(db["data"], list):
        db["data"] = []

    return db


# ==========================
# PDF TEXT EXTRACTION (Better than PyPDF2)
# ==========================
def extract_pdf_text(path):
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:10]:  # first 10 pages
                content = page.extract_text()
                if content:
                    text += content + "\n"
    except:
        pass
    return text


# ==========================
# AI EXTRACTION
# ==========================
def extract_structured_data(slug_id, text):

    prompt = f"""
Return ONLY valid JSON.

Root key must be exactly "{slug_id}"

Structure must strictly follow:

{{
  "{slug_id}": {{
    "overview": {{
        "post_name": "",
        "recruitment_body": "",
        "notification_number": ""
    }},
    "important_dates": {{}},
    "application_fee": {{}},
    "age_limit": {{
        "minimum": "",
        "maximum": "",
        "relaxation": ""
    }},
    "educational_qualification": [],
    "vacancy_details": {{
        "total": "",
        "table": []
    }},
    "selection_process": [],
    "syllabus": {{
        "mathematics": [],
        "reasoning": [],
        "general_awareness": []
    }},
    "medical_standards": {{}},
    "important_instructions": [],
    "important_links": {{
        "links": {{}}
    }}
  }}
}}

Extract full structured data from this text:

{text[:15000]}
"""

    response = model.generate_content(prompt)

    match = re.search(r"\{.*\}", response.text, re.DOTALL)
    if not match:
        raise ValueError("AI did not return valid JSON")

    data = json.loads(match.group(0))
    return data


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

    # Critical fix for your details.html
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
        return

    base = structured_data[slug_id]

    meta_entry = {
        "id": slug_id,
        "master": base["overview"].get("post_name", slug_id),
        "lifecycle": "notification",
        "phase": "",
        "region": "",
        "notification_type": "detailed",
        "type": "Recruitment",
        "status": "Active",
        "url": base["important_links"]["links"].get("Official Website", ""),
        "last_updated": datetime.now().strftime("%Y-%m-%d")
    }

    db["data"].insert(0, meta_entry)

    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)


# ==========================
# MAIN ENGINE
# ==========================
def run_engine():

    db = load_events()
    existing_ids = {item["id"] for item in db["data"]}

    for file in os.listdir(PDF_DIR):

        if not file.endswith(".pdf"):
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
            print(f"❌ Error in {file}: {e}")


if __name__ == "__main__":
    run_engine()