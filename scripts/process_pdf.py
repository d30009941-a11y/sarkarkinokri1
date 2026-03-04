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
    except Exception as e:
        print(f"PDF Read Error: {e}")
        return ""

def run():
    PDF_DIR = "notification/"
    EVENTS_FILE = "data/events.json"
    JOBS_DIR = "data/jobsdata/"

    if not os.path.exists(EVENTS_FILE):
        with open(EVENTS_FILE, "w") as f: json.dump({"data": []}, f)

    with open(EVENTS_FILE, "r") as f: db = json.load(f)
    existing_ids = {item['id'] for item in db['data']}

    files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]
    print(f"Found {len(files)} PDFs in folder.")

    for file in files:
        slug_id = file.lower().replace(".pdf", "").replace(" ", "-")[:40]
        if slug_id in existing_ids:
            print(f"Skipping {slug_id}, already exists.")
            continue

        print(f"Processing: {file}...")
        text = extract_text(os.path.join(PDF_DIR, file))
        
        prompt = f"Extract job info from this text. Return ONLY JSON with fields: master, date, id, details: {{post, vacancy, eligibility, last_date}}. ID: {slug_id}. Text: {text[:2500]}"
        
        try:
            response = model.generate_content(prompt)
            print(f"AI Response received for {slug_id}")
            
            # JSON Clean up
            raw_text = response.text
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                data["id"] = slug_id
                data["official_link"] = f"notification/{file}"

                # Save individual file
                os.makedirs(JOBS_DIR, exist_ok=True)
                with open(f"{JOBS_DIR}{slug_id}.json", "w") as jf:
                    json.dump(data, jf, indent=4)
                
                # Update main list
                db['data'].insert(0, data)
                print(f"Successfully added {slug_id} to events.json")
            else:
                print(f"Could not find JSON in AI response for {file}")

        except Exception as e:
            print(f"Failed to process {file}: {e}")

    with open(EVENTS_FILE, "w") as f:
        json.dump(db, f, indent=4)
    print("Job Completed.")

if __name__ == "__main__":
    run()
