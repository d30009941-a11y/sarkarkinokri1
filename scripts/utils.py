import os
import time
import json
import re
import itertools
from google import genai

# =====================================
# CONFIGURATION & KEYS
# =====================================
STABLE_MODEL = "gemini-1.5-flash"  # Use stable to avoid 404
MIN_INTERVAL = 4.5  # Safe for 15 RPM Free Tier

API_KEYS = [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 4) if os.getenv(f"GEMINI_API_KEY_{i}")]
if not API_KEYS:
    raise RuntimeError("❌ No Gemini API Keys found")

key_cycle = itertools.cycle(API_KEYS)
LAST_CALL_TIME = 0

# =====================================
# CORE UTILITIES
# =====================================
def get_client():
    key = next(key_cycle)
    print(f"🔑 Using API Key: {key[-4:].rjust(4,'*')}")  # Show last 4 chars for reference
    return genai.Client(api_key=key), key

def wait_for_rate_limit():
    global LAST_CALL_TIME
    now = time.time()
    elapsed = now - LAST_CALL_TIME
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    LAST_CALL_TIME = time.time()

def clean_json_response(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("No valid JSON found in AI response")

# =====================================
# THE SAFE GENERATE FUNCTION
# =====================================
def safe_generate(prompt, retries=5):
    wait_time = 5
    for attempt in range(retries):
        try:
            wait_for_rate_limit()
            client, key_used = get_client()
            
            print(f"🤖 AI Attempt {attempt+1} using key ending with {key_used[-4:]}")
            
            response = client.models.generate_content(
                model=STABLE_MODEL,
                contents=prompt
            )
            
            return clean_json_response(response.text)

        except Exception as e:
            print(f"⚠ Attempt {attempt+1} failed with key ending {key_used[-4:]}: {e}")
            if attempt < retries - 1:
                print(f"⏳ Exponential Backoff: Waiting {wait_time}s...")
                time.sleep(wait_time)
                wait_time *= 2
            else:
                print("❌ All retries exhausted for this prompt.")
                return None  # Pipeline moves to next PDF