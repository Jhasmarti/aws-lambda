"""
             Whenever a new .txt file is added, it automatically
             generates an S3 event and triggers lambda_handler().
"""

import os
import time
import uuid
from lambda_function import lambda_handler


class AutomationContext:
    """Mock Lambda Context for automated invocations"""
    def __init__(self):
        self.aws_request_id = f"AUTO-{uuid.uuid4().hex[:8]}"


# Watch directory: MyLambdaProject/incoming_files
WATCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "incoming_files")
os.makedirs(WATCH_DIR, exist_ok=True)

processed_files = set()

print(f"AUTOMATION ACTIVE: Watching folder:\n   {WATCH_DIR}")
print("Drop any .txt file into this folder to trigger Lambda!")
print("   (Press Ctrl + C in CMD to stop automation)")


try:
    while True:
        # Check files in incoming_files folder
        current_files = os.listdir(WATCH_DIR)

        for filename in current_files:
            file_path = os.path.join(WATCH_DIR, filename)

            # Agar nayi file aayi hai aur pehle process nahi hui
            if filename not in processed_files and os.path.isfile(file_path):
                print(f"\n[NEW FILE DETECTED]: '{filename}' -> Triggering Lambda...")

                # 1. Dynamically create S3 ObjectCreated event
                simulated_event = {
                    "Records": [
                        {
                            "s3": {
                                "bucket": {"name": "automated-incoming-bucket"},
                                "object": {"key": os.path.join("incoming_files", filename)}
                            }
                        }
                    ]
                }

                # 2. Automatically invoke Lambda
                context = AutomationContext()
                response = lambda_handler(simulated_event, context)

                # 3. Print status
                if response.get("statusCode") == 200:
                    print(f"[PROCESSED SUCCESSFULLY]: Check 'output/result.json'!")
                else:
                    print(f"[FAILED]: {response.get('body')}")

                processed_files.add(filename)

        time.sleep(2)  # Har 2 second mein check karega

except KeyboardInterrupt:
    print("\nAutomation stopped by user.")