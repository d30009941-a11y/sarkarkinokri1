import os, json, re
from datetime import datetime

JOBS_DIR = "data/jobsdata/"
EVENTS_DIR = "data/events/"
PDF_DIR = "notification/"

os.makedirs(EVENTS_DIR, exist_ok=True)

def run_event_controller():
    # Matches PDFs to Master IDs using Regex to save API quota
    master_ids = {f.replace(".json", ""): os.path.join(JOBS_DIR, f) for f in os.listdir(JOBS_DIR)}

    for file in os.listdir(PDF_DIR):
        if not file.endswith(".pdf"): continue
        event_file = os.path.join(EVENTS_DIR, "master_events.json") # Simplified for Analysis
        # ... (Insert your locked Regex matching logic here) ...
    print("✅ Event processing complete.")

if __name__ == "__main__": run_event_controller()
