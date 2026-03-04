import os
import json
import re
import google.generativeai as genai
from PyPDF2 import PdfReader
from datetime import datetime

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

    with open(EVENTS_FILE, "r") as f: db = json.load(f)
    existing_ids = {item['id'] for item in db['data']}

    for file in os.listdir(PDF_DIR):
        if not file.endswith(".pdf"): continue
        
        # ID Format: org-shortcode + notification-code + year (as per your rules)
        # Hum filename ko hi ID maan rahe hain abhi ke liye
        slug_id = file.lower().replace(".pdf", "").replace(" ", "-")[:40]
        
        if slug_id in existing_ids:
            print(f"Skipping {slug_id}...")
            continue

        print(f"Processing {file}...")
        text = extract_text(os.path.join(PDF_DIR, file))
        
        # AI ko wahi purana Meta format sikhane ka prompt
        prompt = f"""
        Extract job info from this text. Return ONLY JSON.
        Required Format (Strictly follow your meta):
        {{
          "id": "{slug_id}",
          "master": "Short Exam Name",
          "lifecycle": "registration/notification/admit_card/result",
          "phase": "mains/prelims/etc",
          "region": "state or central",
          "notification_type": "detailed/short",
          "type": "Recruitment/Admission/Result",
          "status": "Active/Ongoing",
          "url": "official website link",
          "last_updated": "{datetime.now().strftime('%Y-%m-%d')}",
          "details": {{
             "post": "name",
             "vacancy": "number",
             "eligibility": "criteria",
             "last_date": "YYYY-MM-DD"
          }}
        }}
        Text: {text[:2500]}
        """
        
        try:
            response = model.generate_content(prompt)
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                
                # Save individual file for details.html
                os.makedirs(JOBS_DIR, exist_ok=True)
                with open(f"{JOBS_DIR}{slug_id}.json", "w") as jf:
                    json.dump(data, jf, indent=4)

                # Add to main events list (Exactly like your old file)
                # Hum details ko remove kar dete hain list se taaki file heavy na ho
                list_entry = {k: v for k, v in data.items() if k != 'details'}
                db['data'].insert(0, list_entry)
                
                print(f"Added {slug_id} successfully.")
        except Exception as e:
            print(f"Error: {e}")

    with open(EVENTS_FILE, "w") as f:
        json.dump(db, f, indent=4)

if __name__ == "__main__":
    run()
