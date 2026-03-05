import os
import subprocess
import sys
from datetime import datetime

# Get absolute paths to ensure GitHub Runner finds the folders correctly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

def run_step(script_name):
    print(f"\n{'='*40}")
    print(f"🚀 RUNNING: {script_name}")
    print(f"{'='*40}")

    script_path = os.path.join(SCRIPT_DIR, script_name)

    try:
        # Integrated your stream handling for better logging visibility
        subprocess.run(
            [sys.executable, script_path],
            check=True,
            cwd=ROOT_DIR,
            stdout=sys.stdout, # Streams AI logs directly to console
            stderr=sys.stderr  # Streams API errors directly to console
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR in {script_name}: {e}")
        return False

def main():
    start_time = datetime.now()

    # 1. Folder Guard: Ensures directory structure exists before processing
    required_dirs = [
        os.path.join(ROOT_DIR, "notification"),
        os.path.join(ROOT_DIR, "data/jobsdata"),
        os.path.join(ROOT_DIR, "data/events")
    ]

    for d in required_dirs:
        if not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
            print(f"📁 Initialized directory: {d}")

    # 2. Key Guard: Prevents pipeline from starting if no keys are found
    keys = [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 4)]
    active_keys = [k for k in keys if k]

    if not active_keys:
        print("🛑 CRITICAL: No Gemini API keys found. Resolve keys to continue.")
        sys.exit(1)
    
    print(f"🔑 Keys Ready: {len(active_keys)} keys available for rotation.")

    # 3. Step-by-Step Execution Sequence
    if not run_step("process_jobdata.py"):
        print("🛑 Pipeline Halted: Job extraction failed.")
        sys.exit(1)

    if not run_step("process_events.py"):
        print("🛑 Pipeline Halted: Event sync failed.")
        sys.exit(1)

    # 4. Success Reporting
    duration = datetime.now() - start_time
    print(f"\n{'='*40}")
    print("✅ PIPELINE SUCCESSFUL")
    print(f"⏱️ Total Execution Time: {duration}")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*40}")

if __name__ == "__main__":
    main()
