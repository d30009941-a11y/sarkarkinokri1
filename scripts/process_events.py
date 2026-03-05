import os
import json
from datetime import datetime

JOBS_DIR = "data/jobsdata/"
EVENTS_DIR = "data/events/"
os.makedirs(EVENTS_DIR, exist_ok=True)

def load_events(master_id):
    path = os.path.join(EVENTS_DIR, f"{master_id}.json")
    if not os.path.exists(path):
        return {"data":[]}
    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)

def save_events(master_id, data):
    path = os.path.join(EVENTS_DIR, f"{master_id}.json")
    with open(path,"w",encoding="utf-8") as f:
        json.dump(data,f,indent=4)

def run_events():
    for job_file in os.listdir(JOBS_DIR):
        if not job_file.endswith(".json"): continue
        master_id = job_file.replace(".json","")
        job_path = os.path.join(JOBS_DIR, job_file)
        with open(job_path,"r",encoding="utf-8") as f:
            job_data = json.load(f)

        events = load_events(master_id)
        existing_ids = {item["id"] for item in events["data"]}

        # Example: one event per job for testing
        if master_id not in existing_ids:
            entry = {
                "id": master_id,
                "master_id": master_id,
                "title": job_data.get(master_id,{}).get("overview",{}).get("post_name", master_id),
                "type":"Recruitment",
                "status":"Active",
                "official_url": job_data.get(master_id,{}).get("important_links",{}).get("links",{}).get("Official Website",""),
                "event_date": datetime.now().strftime("%d-%m-%Y"),
                "updated_on": datetime.now().strftime("%d-%m-%Y"),
                "is_new": True,
                "filename": job_file
            }
            events["data"].insert(0,entry)
            save_events(master_id, events)
            print(f"✅ Event updated for {master_id}")

if __name__ == "__main__":
    run_events()