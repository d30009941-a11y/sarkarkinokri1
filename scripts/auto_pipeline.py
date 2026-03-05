import subprocess, sys, os

def main():
    # Step 1: Run Job Extraction (AI)
    print("🚀 Starting Job Extraction...")
    subprocess.run([sys.executable, "scripts/process_jobdata.py"], check=True)

    # Step 2: Run Event Linking (Regex)
    print("📅 Starting Event Sync...")
    subprocess.run([sys.executable, "scripts/process_events.py"], check=True)

if __name__ == "__main__": main()
