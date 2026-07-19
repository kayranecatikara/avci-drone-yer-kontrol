import os
import json

transcript_path = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\.system_generated\logs\transcript.jsonl"

if os.path.exists(transcript_path):
    print("Transcript found! Searching for recent USER_INPUT steps:")
    with open(transcript_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                step = json.loads(line)
                if step.get("type") == "USER_INPUT":
                    print(f"\nStep {step.get('step_index')}:")
                    print(f"Content: {step.get('content')}")
                    # Print the full JSON object to inspect attached media/files metadata
                    print("JSON keys:", step.keys())
                    if "media" in step or "files" in step or "attachments" in step:
                        print("Media/Attachments found:")
                        for k in ["media", "files", "attachments"]:
                            if k in step:
                                print(f" - {k}: {step[k]}")
            except Exception as e:
                pass
else:
    print("Transcript not found.")
