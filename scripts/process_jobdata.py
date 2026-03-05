import os, re, json, time, pdfplumber
from google import genai
from datetime import datetime

# CONFIGURATION
PDF_DIR, JOBS_DIR = "notification/", "data/jobsdata/"
STABLE_MODEL = "gemini-1.5-flash" # Fixes 404

class GeminiRotator:
    def __init__(self):
        self.keys = [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 4) if os.getenv(f"GEMINI_API_KEY_{i}")]
        if not self.keys: raise RuntimeError("❌ No API keys")
        self.index = 0
        self.client = genai.Client(api_key=self.keys[0])

    def rotate(self):
        self.index = (self.index + 1) % len(self.keys)
        self.client = genai.Client(api_key=self.keys[self.index])

rotator = GeminiRotator()

def generate_hardened_slug(text, filename):
    # Strict Format: org-shortcode + notification-code + year
    sample = text[:2000].lower()
    org = "govt"
    for k in ["rrb", "ssc", "upsc", "nta", "rbi", "ibps"]:
        if k in sample: org = k; break
    
    notif_match = re.search(r'(cen|advt|notice)\s*(\d+[\-/]\d{4})', sample)
    if notif_match:
        code = notif_match.group(2).replace("/", "-")
        slug = f"{org}-{notif_match.group(1)}-{code}"
    else:
        slug = f"{org}-{re.sub(r'[^a-z0-9]', '-', filename.lower()[:20])}"
    return slug[:40].strip("-")

def run_engine():
    os.makedirs(JOBS_DIR, exist_ok=True)
    for file in os.listdir(PDF_DIR):
        if not file.lower().endswith(".pdf"): continue
        path = os.path.join(PDF_DIR, file)
        
        with pdfplumber.open(path) as pdf:
            text = "\n".join([p.extract_text() or "" for p in pdf.pages[:10]])
            
        slug_id = generate_hardened_slug(text, file)
        final_path = os.path.join(JOBS_DIR, f"{slug_id}.json")
        if os.path.exists(final_path): continue

        prompt = f"Return ONLY valid JSON. Root key: '{slug_id}'. Extract recruitment data: {text[:12000]}"
        
        for _ in range(len(rotator.keys) * 2):
            try:
                res = rotator.client.models.generate_content(model=STABLE_MODEL, contents=prompt)
                match = re.search(r"\{.*\}", res.text, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    with open(final_path, "w") as f: json.dump(data, f, indent=4)
                    print(f"✅ Hardened: {slug_id}")
                    time.sleep(15) # Lengthy execution to avoid 429
                    break
            except Exception as e:
                print(f"⚠️ Error: {str(e)[:50]}")
                rotator.rotate()
                time.sleep(10)

if __name__ == "__main__": run_engine()
