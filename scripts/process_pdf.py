import os
import sys
import json
from datetime import datetime
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def process_pdf(pdf_path):
    model = genai.GenerativeModel("gemini-1.5-flash")
    pdf_file = genai.upload_file(path=pdf_path)
    
    # Prompt tailored to your details.html "renderEngine"
    prompt = """Analyze this recruitment PDF and return ONLY JSON:
    {
      "master_id": "org-shortcode-notif-year (e.g., rrb-cen-01-2024)",
      "lifecycle": "notification/admit_card/result/answer_key/dv",
      "overview": {
        "post_name": "Full Post Name",
        "recruitment_body": "Organization Name",
        "notification_number": "Official Notif No."
      },
      "important_dates": { "Start Date": "", "Last Date": "", "Exam Date": "" },
      "application_fee": { "General": "", "SC/ST": "" },
      "important_links": {
        "links": { "Download Notification": "url", "Official Website": "url" }
      },
      "short_info": "2-3 lines for fallback"
    }"""
    
    response = model.generate_content([prompt, pdf_file])
    data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
    
    master_id = data['master_id']
    child_id = f"{master_id}-{data['lifecycle']}"
    
    # 1. Update data/events.json
    update_events(data, child_id)
    
    # 2. Create data/jobsdata/{child_id}.json (Lightweight individual file)
    job_data_path = f"data/jobsdata/{child_id}.json"
    os.makedirs('data/jobsdata', exist_ok=True)
    with open(job_data_path, 'w') as f:
        # Wrapping in child_id key as your details.html expects: json[id]
        json.dump({child_id: data}, f, indent=2)

def update_events(data, child_id):
    path = 'data/events.json'
    with open(path, 'r+') as f:
        events = json.load(f)
        
        # New entry for index.html feed
        new_entry = {
            "id": child_id,
            "master": data['master_id'],
            "type": data['lifecycle'].capitalize(),
            "status": "Active",
            "url": data['important_links']['links'].get('Official Website', '#'),
            "dates": data['important_dates']
        }
        events['data'].insert(0, new_entry)
        f.seek(0)
        json.dump(events, f, indent=2)
        f.truncate()

if __name__ == "__main__":
    process_pdf(sys.argv[1])
