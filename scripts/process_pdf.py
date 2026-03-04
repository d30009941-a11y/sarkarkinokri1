import os
import json
import re
import google.generativeai as genai
from PyPDF2 import PdfReader

# API Configuration
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def get_pdf_text(path):
    try:
        reader = PdfReader(path)
        return " ".join([page.extract_text() for page in reader.pages[:3]])
    except Exception as e:
        print(f"Error reading PDF {path}: {e}")
        return ""

def clean_ai_json(text):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return match.group(0) if match else text

def process_portal_updates():
    PDF_DIR = "notification/"
    DATA_DIR = "data/"
    JOBS_DATA_DIR = "data/jobsdata/"
    EVENTS_FILE = os.path.join(DATA_DIR, "events.json")
    
    # 1. Automatic Folder/File Creation (Long term safety)
    if not os.path.exists(JOBS_DATA_DIR):
        os.makedirs(JOBS_DATA_DIR)
        print(f"Created directory: {JOBS_DATA_DIR}")

    if not os.path.exists(EVENTS_FILE) or os.stat(EVENTS_FILE).st_size == 0:
        with open(EVENTS_FILE, "w") as f:
            json.dump({"data": []}, f)
        print("Initialized empty events.json")

    # Load existing data
    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)

    processed_ids = {item['id'] for item in db['data']}
    new_entries = []

    for filename in os.listdir(PDF_DIR):
        if not filename.endswith(".pdf"): continue
        
        # Unique ID based on filename
        slug_id = filename.lower().replace(".pdf", "").replace(" ", "-")
        if slug_id in processed_ids: continue

        print(f"AI Analyzing: {filename}...")
        raw_text = get_pdf_text(os.path.join(PDF_DIR, filename))
        
        # Professional Prompt (With strict ID instruction)
        prompt = f"""
        Extract job details from the text. Return ONLY JSON.
        ID Format: org-shortname-notification-year (e.g., rrb-cen-01-2024)
        JSON Template:
        {{
            "id": "{slug_id}",
            "master": "Job Title",
            "type": "Recruitment/Result/Admit Card",
            "lifecycle": "lowercase type",
            "status": "active",
            "date": "2026-03-04",
            "details": {{
                "post": "Post name",
                "vacancy": "Total vacancy",
                "eligibility": "Qualification",
                "last_date": "Deadline"
            }}
        }}
        Text: {raw_text[:3000]}
        """

        try:
            response = model.generate_content(prompt)
            job_info = json.loads(clean_ai_json(response.text))
            job_info["official_link"] = f"notification/{filename}"
            
            # Save detail file for details.html
            with open(f"{JOBS_DATA_DIR}{slug_id}.json", "w") as jf:
                json.dump(job_info, jf, indent=4)
            
            new_entries.append(job_info)
            print(f"Successfully processed: {slug_id}")
        except Exception as e:
            print(f"Skipping {filename} due to error: {e}")

    if new_entries:
        db['data'] = new_entries + db['data']
        with open(EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
        print(f"Update Complete! {len(new_entries)} items added.")

if __name__ == "__main__":
    process_portal_updates()
