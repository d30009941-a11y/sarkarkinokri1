import os
import json
import re
from datetime import datetime
import pdfplumber

# ==========================================
# CONFIGURATION
# ==========================================
JOBS_DIR = "data/jobsdata/"
EVENTS_DIR = "events/"          # New folder for per-master JSON
PDF_DIR = "notification/"       # All PDFs, including event notices
MAX_PAGES = 5                   # Only read first few pages for performance

# Ensure events folder exists
os.makedirs(EVENTS_DIR, exist_ok=True)

# ==========================================
# PDF TEXT EXTRACTION
# ==========================================
def extract_pdf_text(path, pages=MAX_PAGES):
    try:
        with pdfplumber.open(path) as pdf:
            page_count = min(len(pdf.pages), pages)
            text = "\n".join([p.extract_text() or "" for p in pdf.pages[:page_count]])
            return text.lower()
    except:
        return ""

# ==========================================
# RUN EVENT CONTROLLER
# ==========================================
def run_event_controller():
    today = datetime.now()

    # Load jobsdata master IDs
    master_ids = {f.replace(".json", ""): os.path.join(JOBS_DIR, f)
                  for f in os.listdir(JOBS_DIR) if f.endswith(".json")}

    # Process all PDFs
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
    for file in pdf_files:
        path = os.path.join(PDF_DIR, file)
        text = extract_pdf_text(path)

        # --- MASTER ID MATCH ---
        master_id = None
        master_static = {}
        for mid, mid_path in master_ids.items():
            code_search = re.search(r'\d+-\d{4}', mid)
            if code_search and code_search.group(0).replace("-", "") in text.replace("-", "").replace("/", ""):
                master_id = mid
                try:
                    with open(mid_path, "r", encoding="utf-8") as f:
                        job_json = json.load(f)
                        node = job_json.get(mid, {})
                        overview = node.get("overview", {})
                        master_static = {
                            "job_name": overview.get("post_name", master_id.replace("-", " ").upper()),
                            "recruiting_board": overview.get("recruiting_board", "")
                        }
                except:
                    master_static = {}
                break

        # --- LIFECYCLE AND PHASE ---
        lifecycle_match = re.search(r'(notification|admit card|result|answer key|dv|interview)', text)
        lifecycle = lifecycle_match.group(1).replace(" ", "_") if lifecycle_match else "latest_job"

        phase_match = re.search(r'phase\s*(\d+)', text)
        phase = f"phase{phase_match.group(1)}" if phase_match else "phase1"

        # Generate child ID
        child_id = f"{master_id or 'orphan'}-{lifecycle}-{phase}"

        # --- DETERMINE EVENT FILE PATH ---
        event_file = os.path.join(EVENTS_DIR, f"{master_id or 'orphan'}.json")

        # If file doesn't exist, create empty structure
        if not os.path.exists(event_file):
            with open(event_file, "w", encoding="utf-8") as f:
                json.dump({"master_id": master_id or "orphan", "events": []}, f, indent=4)

        # Load existing events for this master
        try:
            with open(event_file, "r", encoding="utf-8") as f:
                event_json = json.load(f)
        except:
            event_json = {"master_id": master_id or "orphan", "events": []}

        # --- SKIP IF CHILD ID ALREADY EXISTS ---
        existing_child_ids = {e.get("child_id") for e in event_json.get("events", [])}
        if child_id in existing_child_ids:
            continue

        # --- EVENT TYPE AND OFFICIAL URL ---
        event_type = "latest_job"
        if "result" in text: event_type = "result"
        elif "admit card" in text: event_type = "admit_card"
        elif "answer key" in text: event_type = "answer_key"

        url_match = re.search(r'https?://(?:www\.)?[\w\-\.]+\.(?:gov|nic|in|org|com)(?:/[\w\-\./?%&=]*)?', text)
        official_url = url_match.group(0) if url_match else f"https://yourdomain.com/notification/{file}"

        # --- EVENT DATE AND NEW TAG ---
        date_match = re.search(r'(\d{2}[-/]\d{2}[-/]\d{4})', text)
        event_date = date_match.group(1) if date_match else today.strftime("%d-%m-%Y")
        file_time = datetime.fromtimestamp(os.path.getmtime(path))
        is_new = (today - file_time).days < 3

        # --- FINAL EVENT ENTRY ---
        entry = {
            "child_id": child_id,
            "master_id": master_id,
            "title": master_static.get("job_name", child_id.replace("-", " ").upper()),
            "type": event_type,
            "status": "Active",
            "official_url": official_url,
            "event_date": event_date,
            "updated_on": today.strftime("%d-%m-%Y"),
            "is_new": is_new,
            "filename": file,
            "recruiting_board": master_static.get("recruiting_board", "")
        }

        # Insert new event at top
        event_json["events"].insert(0, entry)

        # --- ATOMIC SAVE ---
        temp_path = event_file + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(event_json, f, indent=4)
        os.replace(temp_path, event_file)

    print("✅ Event processing complete.")


if __name__ == "__main__":
    run_event_controller()
