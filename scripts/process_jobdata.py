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
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-3.1-flash-lite-preview"
MAX_RETRIES = 5
INITIAL_WAIT = 5  # seconds
PDF_DIR = "notification/"
JOBS_DIR = "data/jobsdata/"

client = genai.Client(api_key=API_KEY)

# ==========================
# HELPER FUNCTIONS
# ==========================
def extract_pdf_text(path, pages=20):
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for p in pdf.pages[:pages]:
                content = p.extract_text()
                if content:
                    text += content + "\n"
    except Exception as e:
        print("PDF extraction error:", e)
    return text

def safe_json_load(text):
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except:
        pass
    return None

def generate_slug(filename, text_sample=None):
    # Use master ID or fallback to filename
    if text_sample:
        code_match = re.search(r'(cen|advt|notification|notice|phase)\s*(?:no\.?|number)?\s*[:\-]?\s*(\d+[\-/]\d{2,4})', text_sample.lower())
        if code_match:
            prefix = code_match.group(1)[:4]
            code = code_match.group(2).replace("/", "-")
            return f"{prefix}-{code}".lower()
    # fallback
    return filename.lower().replace(".pdf","").replace(" ","-")[:50]

def enforce_schema(slug_id, data):
    base = data.get(slug_id, {})
    base.setdefault("overview", {})
    base.setdefault("important_dates", {})
    base.setdefault("application_fee", {})
    base.setdefault("age_limit", {"minimum":"","maximum":"","relaxation":""})
    base.setdefault("educational_qualification", [])
    base.setdefault("vacancy_details", {"total":"","table":[]})
    base.setdefault("selection_process", [])
    base.setdefault("syllabus", {"mathematics":[], "reasoning":[], "general_awareness":[]})
    base.setdefault("medical_standards", {})
    base.setdefault("important_instructions", [])
    base.setdefault("important_links", {"links":{}})
    data[slug_id] = base
    return data

def save_job_json(slug_id, data):
    os.makedirs(JOBS_DIR, exist_ok=True)
    with open(os.path.join(JOBS_DIR, f"{slug_id}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def extract_structured_data(slug_id, text):
    prompt = f"""
Return ONLY valid JSON.
Root key must be exactly "{slug_id}"
Extract structured recruitment data from this notification text:
{text[:12000]}
"""
    wait = INITIAL_WAIT
    for attempt in range(MAX_RETRIES):
        try:
            print(f"🤖 AI Attempt {attempt+1} for {slug_id}")
            response = client.models.generate_content(model=MODEL, contents=prompt)
            structured = safe_json_load(response.text)
            if structured:
                return structured
            raise ValueError("AI did not return valid JSON")
        except Exception as e:
            print(f"⚠ Attempt {attempt+1} failed: {e}")
            if attempt < MAX_RETRIES -1:
                time.sleep(wait)
                wait *= 2
            else:
                raise e

# ==========================
# MAIN ENGINE
# ==========================
def run_engine():
    if not os.path.exists(PDF_DIR):
        print("❌ Notification folder not found.")
        return

    for file in os.listdir(PDF_DIR):
        if not file.lower().endswith(".pdf"):
            continue

        path = os.path.join(PDF_DIR, file)
        text = extract_pdf_text(path)
        slug_id = generate_slug(file, text_sample=text)

        # Skip if already exists
        if os.path.exists(os.path.join(JOBS_DIR, f"{slug_id}.json")):
            print(f"⏩ Skipped existing: {slug_id}")
            continue

        try:
            structured_data = extract_structured_data(slug_id, text)
            structured_data = enforce_schema(slug_id, structured_data)
            save_job_json(slug_id, structured_data)
            print(f"✅ Successfully saved: {slug_id}")
        except Exception as e:
            print(f"❌ Failed {file}: {e}")

if __name__ == "__main__":
    run_engine()