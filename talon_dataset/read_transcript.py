import os

transcript_path = r"C:\Users\Zeylo\.gemini\antigravity\brain\36eff956-7e9e-4245-954f-3ac1eb798a93\.system_generated\logs\transcript.jsonl"

if os.path.exists(transcript_path):
    print("Transcript found! Reading the last few lines:")
    with open(transcript_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    print(f"Total lines: {len(lines)}")
    # Print the last 5 lines (which represent the recent steps)
    for idx, line in enumerate(lines[-5:]):
        print(f"\n--- Line {len(lines) - 5 + idx} ---")
        # Print only the first 500 chars to avoid clutter
        print(line[:1000] + "...")
else:
    print(f"Transcript not found at: {transcript_path}")
