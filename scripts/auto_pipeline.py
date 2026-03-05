import os
import subprocess
import sys
from datetime import datetime

def run_step(script_name):
    """Executes a sub-script and captures the output."""
    print(f"\n{'='*40}")
    print(f"🚀 RUNNING: {script_name}")
    print(f"{'='*40}")
    
    try:
        # Runs the script and streams output to console
        result = subprocess.run([sys.executable, f"scripts/{script_name}"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR in {script_name}: {e}")
        return False

def main():
    start_time = datetime.now()
    
    # 1. Environment Guard
    required_keys = ["GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]
    missing = [k for k in required_keys if not os.getenv(k)]
    if missing:
        print(f"⚠️ WARNING: Missing API Keys: {', '.join(missing)}")
        print("Pipeline will attempt to run with available keys...")

    # 2. Step 1: Ingest PDFs and Generate Rich Master JSONs
    if not run_step("process_jobdata.py"):
        print("🛑 Pipeline Halted: JobData extraction failed.")
        sys.exit(1)

    # 3. Step 2: Sync Events and Update Timelines
    if not run_step("process_events.py"):
        print("🛑 Pipeline Halted: Event synchronization failed.")
        sys.exit(1)

    # 4. Final Summary
    duration = datetime.now() - start_time
    print(f"\n{'='*40}")
    print(f"✅ PIPELINE COMPLETE")
    print(f"⏱️ Total Time: {duration}")
    print(f"📅 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*40}")

if __name__ == "__main__":
    main()
  
