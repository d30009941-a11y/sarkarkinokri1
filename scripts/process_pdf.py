import os
import json
import re
import google.generativeai as genai
from PyPDF2 import PdfReader

# 1. Setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def extract_text(path):
    try:
        reader = PdfReader(path)
        return " ".join([page.extract_text() for page in reader.pages[:3]])
    except: return ""

def run():
    PDF_DIR = "notification/"
    EVENTS_FILE = "data/events.json"
    JOBS_DIR = "data/jobsdata/"

    # Load DB
    with open(EVENTS_FILE, "r") as f: db = json.load(f)
    existing_ids = {item['id'] for item in db['data']}

    for file in os.listdir(PDF_DIR):
        if not file.endswith(".pdf"): continue
        
        # ID Generation (Strict Format)
        slug_id = file.lower().replace(".pdf", "").replace(" ", "-")[:40]
        if slug_id in existing_ids: continue

        print(f"Processing {file}...")
        text = extract_text(os.path.join(PDF_DIR, file))
        
        prompt = f"Extract job info from this text. Return ONLY JSON. ID: {slug_id}. Text: {text[:2000]}"
        try:
            response = model.generate_content(prompt)
            raw_json = re.search(r'\{.*\}', response.text, re.DOTALL).group(0)
            data = json.loads(raw_json)
            data["id"] = slug_id
            data["official_link"] = f"notification/{file}"

            # Save individual file
            with open(f"{JOBS_DIR}{slug_id}.json", "w") as jf: json.dump(data, jf)
            # Update main list
            db['data'].insert(0, data)
        except Exception as e: print(f"Error: {e}")

    with open(EVENTS_FILE, "w") as f: json.dump(db, f, indent=4)

if __name__ == "__main__":
    run()
