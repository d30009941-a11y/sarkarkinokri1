import os
import json
import re
import google.generativeai as genai
from PyPDF2 import PdfReader
from datetime import datetime

# Setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def extract_pdf_text(path):
    try:
        reader = PdfReader(path)
        # Pehle 5 pages scan karte hain kyunki recruitment details shuru mein hoti hain
        return " ".join([p.extract_text() for p in reader.pages[:5]])
    except: return ""

def run_engine():
    PDF_DIR = "notification/"
    JOBS_DIR = "data/jobsdata/"
    EVENTS_FILE = "data/events.json"

    # Load Main DB
    with open(EVENTS_FILE, "r") as f: db = json.load(f)
    existing_ids = {item['id'] for item in db['data']}

    for file in os.listdir(PDF_DIR):
        if not file.endswith(".pdf"): continue
        
        # ID as per your rules (org-code-year)
        slug_id = file.lower().replace(".pdf", "").replace(" ", "-")[:40]
        if slug_id in existing_ids: continue

        print(f"🚀 Expert Extraction Started: {file}")
        text = extract_pdf_text(os.path.join(PDF_DIR, file))

        # --- SUPER RICH PROMPT ---
        prompt = f"""
        Act as a Govt Job Notification Expert. Analyze the text and return ONLY a JSON object.
        The JSON key must be exactly "{slug_id}".
        
        Fields to extract:
        1. overview: {{post_name, recruitment_body, notification_number}}
        2. important_dates: {{Application Start Date, Last Date to Apply, Last Date Fee Payment, Correction Window, CBT Exam Date}}
        3. application_fee: {{General/OBC/EWS, SC/ST/Female, Payment Mode}}
        4. age_limit: {{Min, Max, Relaxation}}
        5. educational_qualification: (detailed list)
        6. vacancy_details: {{total, table: [{{Region/Force, UR, OBC, SC, ST, EWS, Total}}]}}
        7. selection_process: (List of stages)
        8. syllabus: {{mathematics: [], reasoning: [], general_awareness: []}}
        9. medical_standards: {{category, vision, height, chest}}
        10. important_instructions: (List of 4-5 key points)
        11. important_links: {{Apply Now, Official Website}}

        Text: {text[:4000]}
        """

        try:
            response = model.generate_content(prompt)
            json_str = re.search(r'\{.*\}', response.text, re.DOTALL).group(0)
            rich_data = json.loads(json_str)

            # Individual Rich JSON save (for details.html)
            os.makedirs(JOBS_DIR, exist_ok=True)
            with open(f"{JOBS_DIR}{slug_id}.json", "w") as jf:
                json.dump(rich_data, jf, indent=4)

            # Update Index (events.json) - Meta Only
            # Hum meta-data AI ke response se hi extract karenge
            meta_entry = {
                "id": slug_id,
                "master": rich_data[slug_id]['overview']['post_name'],
                "lifecycle": "notification",
                "phase": "",
                "region": rich_data[slug_id].get('region', ""),
                "notification_type": "detailed",
                "type": "Recruitment",
                "status": "Active",
                "url": rich_data[slug_id]['important_links'].get('Official Website', ""),
                "last_updated": datetime.now().strftime('%Y-%m-%d')
            }
            db['data'].insert(0, meta_entry)
            print(f"✅ Rich Data Saved for {slug_id}")

        except Exception as e:
            print(f"❌ Error in {file}: {e}")

    # Save final DB
    with open(EVENTS_FILE, "w") as f:
        json.dump(db, f, indent=4)

if __name__ == "__main__":
    run_engine()
