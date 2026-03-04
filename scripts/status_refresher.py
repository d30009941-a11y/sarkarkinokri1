import json
import os
from datetime import datetime

def run_janitor():
    path = 'data/events.json'
    if not os.path.exists(path): return

    today = datetime.now()
    with open(path, 'r+') as f:
        events = json.load(f)
        for entry in events['data']:
            # Case 3: Date logic (Looking for 'Last Date' or 'end')
            dates = entry.get('dates', {})
            last_date_str = dates.get('Last Date') or dates.get('end')
            
            if last_date_str:
                try:
                    last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
                    if today > last_date:
                        entry['status'] = "Application Closed"
                except: continue
        
        f.seek(0)
        json.dump(events, f, indent=2)
        f.truncate()

if __name__ == "__main__":
    run_janitor()
