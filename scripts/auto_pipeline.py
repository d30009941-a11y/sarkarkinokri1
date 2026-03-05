import subprocess
import sys
from datetime import datetime

def run_step(script):
    print(f"\n🚀 Running {script}")
    try:
        subprocess.run([sys.executable, f"scripts/{script}"], check=True)
        return True
    except:
        print(f"❌ Failed: {script}")
        return False

def main():
    start = datetime.now()
    print(f"📅 Pipeline started at {start}")

    if not run_step("process_jobdata.py"): sys.exit(1)
    if not run_step("process_events.py"): sys.exit(1)

    end = datetime.now()
    print(f"✅ Pipeline finished in {end-start}")

if __name__ == "__main__":
    main()