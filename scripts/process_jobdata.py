import os
import re
import json
import time
import pdfplumber
from google import genai
from datetime import datetime

# ==========================================
# 1. ARCHITECTURAL GUARDRAILS
# ==========================================
PDF_DIR, JOBS_DIR = "notification/", "data/jobsdata/"
MODEL_POOL = ["gemini-2.0-flash", "gemini-1.5-pro"]
MAX_RETRIES_PER_KEY = 2 

class GeminiRotator:
    def __init__(self):
        # Load keys 1, 2, and 3 from environment variables
        self.keys = [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 4)]
        self.keys = [k for k in self.keys if k]
        if not self.keys: 
            raise RuntimeError("❌ CRITICAL: No API keys found. Ensure GEMINI_API_KEY_1-3 are set.")
        self.index = 0
        self.update_client()

    def update_client(self): 
        self.client = genai.Client(api_key=self.keys[self.index])

    def rotate(self):
        self.index = (self.index + 1) % len(self.keys)
        print(f"🔄 Rotating to Key #{self.index + 1}...")
        self.update_client()

rotator = GeminiRotator()

# ==========================================
# 2. COLLISION-PROOF SLUG GENERATOR
# ==========================================
def generate_hardened_slug(text, filename):
    sample = text[:3000].lower()
    
    # Organization Detection
    org = "govt"
    org_map = {
        "rrb": "rrb", "railway": "rrb",
        "ssc": "ssc", "staff selection": "ssc",
        "upsc": "upsc", "union public": "upsc",
        "ibps": "ibps", "banking personnel": "ibps",
        "iocl": "iocl", "indian oil": "iocl",
        "nta": "nta", "rbi": "rbi"
    }
    for key, val in org_map.items():
        if key in sample: 
            org = val
            break

    # Exam Name Detection (To prevent ID collisions like CEN 01/2025 across different exams)
    exam_patterns = r'(ntpc|alp|je|technician|cgl|chsl|mts|cpo|gd|steno|group-d)'
    exam_match = re.search(exam_patterns, sample)
    exam = f"-{exam_match.group(1)}" if exam_match else ""

    # Notification Number Regex (Supports CEN, Advt, Notice formats)
    notif_pattern = r'(cen|advt|notification|notice|phase)\s*(?:no\.?|number)?\s*[:\-]?\s*(\d+[\-/]\d{2,4})'
    match = re.search(notif_pattern, sample)
    
    if match:
        prefix = match.group(1)[:4]
        code = match.group(2).replace("/", "-")
        slug = f"{org}{exam}-{prefix}-{code}".lower()
    else:
        # Fallback to cleaned filename if no notification code is found
        clean_name = re.sub(r'[^a-z0-9]', '-', filename.lower().replace('.pdf',''))
        slug = f"{org}{exam}-{clean_name}"
    
    # Clean multiple hyphens and trim to 40 chars for URL stability
    slug = re.sub(r'-+', '-', slug)[:40].strip("-")
    return slug

# ==========================================
# 3. NON-GREEDY JSON EXTRACTOR
# ==========================================
def extract_json_safe(text):
    try:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            json_text = text[start:end+1].strip()
            return json.loads(json_text)
    except Exception as e:
        print(f"⚠️ JSON extraction failed: {e}")
    return None

# ==========================================
# 4. CONTRACT ENFORCEMENT & VISUAL PROTECTION
# ==========================================
def enforce_visual_contract(data, slug_id, filename):
    # Ensure the root key matches our generated slug
    if slug_id not in data: 
        data = {slug_id: data}
    node = data[slug_id]
    
    # Mandatory structural keys for Detail.html
    for key in ["overview", "important_dates", "application_fee", "vacancy_details"]:
        if key not in node: 
            node[key] = {}

    # Fix H1 Master Title (Ensure the page is never blank)
    if not node["overview"].get("post_name"):
        node["overview"]["post_name"] = slug_id.replace("-", " ").upper()
    
    # Recursive Table Enforcement: Forces all "table" keys to be list format
    def fix_tables(obj):
        if isinstance(obj, dict):
            if "table" in obj:
                if not isinstance(obj["table"], list):
                    print(f"⚠️ '{slug_id}': Table format fixed.")
                    obj["table"] = []
                elif len(obj["table"]) == 0:
                    print(f"⚠️ '{slug_id}': Empty table found.")
            for v in obj.values(): fix_tables(v)
        elif isinstance(obj, list):
            for item in obj: fix_tables(item)
    
    fix_tables(node)
    
    # Metadata for debugging and audit
    node["_meta"] = {
        "processed_at": datetime.now().isoformat(),
        "source": filename,
        "engine": "gemini-stabilized-2.0"
    }
    return data

# ==========================================
# 5. EXECUTION ENGINE (Atomic Write & Failover)
# ==========================================
def run_engine():
    os.makedirs(JOBS_DIR, exist_ok=True)
    
    for file in os.listdir(PDF_DIR):
        if not file.lower().endswith(".pdf"): continue
        
        path = os.path.join(PDF_DIR, file)
        
        # Extract Text
        try:
            with pdfplumber.open(path) as pdf:
                page_count = min(20, len(pdf.pages))
                text = "\n".join([p.extract_text() or "" for p in pdf.pages[:page_count]])
        except Exception as e:
            print(f"❌ Could not read PDF {file}: {e}")
            continue
        
        # Generate Deterministic ID
        slug_id = generate_hardened_slug(text, file)
        final_path = os.path.join(JOBS_DIR, f"{slug_id}.json")
        
        if os.path.exists(final_path): 
            print(f"ℹ️ Skipping existing: {slug_id}")
            continue

        # Clean prompt: Truncate at last full paragraph to prevent JSON breakage
        prompt_text = text[:16000]
        if "\n" in prompt_text:
            prompt_text = prompt_text.rsplit("\n", 1)[0]
            
        prompt = f"Return ONLY valid JSON. Root key: '{slug_id}'. Extract COLUMNAR recruitment info: {prompt_text}"

        success = False
        for model_v in MODEL_POOL:
            if success: break
            # Retry cycle across all keys before switching to next model
            for _ in range(len(rotator.keys) * MAX_RETRIES_PER_KEY):
                try:
                    res = rotator.client.models.generate_content(model=model_v, contents=prompt)
                    raw_json = extract_json_safe(res.text)
                    
                    if raw_json:
                        hardened_data = enforce_visual_contract(raw_json, slug_id, file)
                        
                        # Atomic Save: Write to .tmp then rename to prevent corruption
                        temp_file = final_path + ".tmp"
                        with open(temp_file, "w", encoding="utf-8") as f:
                            json.dump(hardened_data, f, indent=4)
                        os.replace(temp_file, final_path)
                        
                        print(f"✅ Successfully Hardened: {slug_id}")
                        success = True
                        break
                except Exception as e:
                    print(f"⚠️ API/Parsing Error for '{slug_id}': {str(e)[:50]}")
                    time.sleep(3)
                    rotator.rotate()

if __name__ == "__main__":
    run_engine()
