

import json
import os
from pathlib import Path

def create_digital_memory(root_directory="."):
    """
    Scans for Gemini CLI log files, extracts user messages, and
    compiles them into a single, sorted JSON file representing
    a "digital episodic memory".
    """
    episodes = []
    log_files = list(Path(root_directory).glob('**/logs.json'))
    print(f"Found {len(log_files)} log files to process.")

    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if not isinstance(data, list):
                    print(f"Skipping non-list JSON in {log_file}")
                    continue

                for entry in data:
                    # We only care about the user's side of the conversation
                    if entry.get('type') == 'user' and 'message' in entry:
                        episodes.append({
                            "timestamp": entry.get('timestamp'),
                            "session_id": entry.get('sessionId'),
                            "message": entry.get('message'),
                            "source_file": str(log_file)
                        })
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {log_file}. File might be corrupt or empty.")
        except Exception as e:
            print(f"An unexpected error occurred with {log_file}: {e}")

    # Sort episodes chronologically
    episodes.sort(key=lambda x: x['timestamp'])

    output_filename = "digital_memory.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(episodes, f, indent=2, ensure_ascii=False)

    print(f"\nSuccessfully created {output_filename} with {len(episodes)} entries.")

if __name__ == "__main__":
    # The script will search from the directory it is run in.
    create_digital_memory()

