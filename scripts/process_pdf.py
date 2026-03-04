import os
import sys
import json
from datetime import datetime
import google.generativeai as genai

# Gemini Setup
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def process_pdf(pdf_path):
    model = genai.GenerativeModel("gemini-1.5-flash")
    pdf_file = genai.upload_file(path=pdf_path)
    
    # User-defined Prompt with Tier-2 Support
    prompt = """
    Analyze this PDF. Return ONLY JSON:
    {
      "master_id": "org-shortcode-notification-year (lowercase, use - for /)",
      "lifecycle": "short_notice/notification/admit_card/answer_key/result",
      "post_name": "Full Post Name",
      "short_info": "2-3 line summary for Tier-2 case",
      "official_url": "Direct link from PDF",
      "dates": {
        "start": "YYYY-MM-DD",
        "end": "YYYY-MM-DD"
      }
    }
    """
    
    response = model.generate_content([prompt, pdf_file])
    data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
    
    # 1. Load Events
    with open('events.json', 'r+') as f:
        events = json.load(f)
        
        # 2. Standby Shield: New lifecycle event marks old ones inactive
        if data['lifecycle'] in ['admit_card', 'result', 'answer_key']:
            for entry in events['data']:
                if entry['master'] == data['master_id']:
                    entry['status'] = "Inactive/Closed"
        
        # 3. Create Child ID
        child_id = f"{data['master_id']}-{data['lifecycle']}"

        # 4. Entry Object (Supports your UI provision)
        new_entry = {
            "id": child_id,
            "master": data['master_id'],
            "title": f"{data['post_name']} - {data['lifecycle'].upper()}",
            "status": "Active Now",
            "short_info": data['short_info'],
            "official_url": data['official_url'],
            "dates": data['dates'],
            "last_updated": datetime.now().strftime("%Y-%m-%d")
        }
        
        events['data'].insert(0, new_entry)
        f.seek(0)
        json.dump(events, f, indent=2)
        f.truncate()

if __name__ == "__main__":
    process_pdf(sys.argv[1])

