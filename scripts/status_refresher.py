import json
import os
from datetime import datetime

def run_janitor():
    path = 'data/events.json'
    if not os.path.exists(path):
        print("events.json not found.")
        return

    today = datetime.now()
    updated = False

    with open(path, 'r+', encoding='utf-8') as f:
        events = json.load(f)

        for entry in events.get('data', []):
            dates = entry.get('dates', {})
            last_date_str = dates.get('Last Date') or dates.get('end')

            if last_date_str:
                try:
                    last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
                    if today > last_date and entry.get('status') != "Application Closed":
                        entry['status'] = "Application Closed"
                        updated = True
                except:
                    continue

        if updated:
            f.seek(0)
            json.dump(events, f, indent=2)
            f.truncate()
            print("Status updated.")
        else:
            print("No lifecycle changes.")

if __name__ == "__main__":
    run_janitor()