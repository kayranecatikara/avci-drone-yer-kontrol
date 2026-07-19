import os
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

transcript_path = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\.system_generated\logs\transcript.jsonl"

if os.path.exists(transcript_path):
    last_user_step = None
    with open(transcript_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                step = json.loads(line)
                if step.get("type") == "USER_INPUT":
                    last_user_step = step
            except Exception:
                pass
                
    if last_user_step:
        print(f"Last User Step Index: {last_user_step.get('step_index')}")
        print(f"Content: {last_user_step.get('content')}")
        for k, v in last_user_step.items():
            if k not in ['content']:
                print(f"{k}: {v}")
    else:
        print("No user input step found.")
else:
    print("Transcript not found.")
