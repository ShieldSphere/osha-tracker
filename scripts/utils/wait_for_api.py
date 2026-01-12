"""
Script to periodically check if the OSHA API rate limit has cleared.
Checks every 5 minutes and notifies when API is accessible again.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
from scripts.utils.check_api_status import check_api_status

print("Monitoring OSHA API rate limit status...")
print("Checking every 5 minutes. Press Ctrl+C to stop.\n")

attempt = 1
while True:
    print(f"[Attempt {attempt}] {time.strftime('%Y-%m-%d %H:%M:%S')}")

    if check_api_status():
        print("\n" + "="*60)
        print("SUCCESS! API is now accessible!")
        print("You can now run syncs without hitting rate limits.")
        print("="*60)
        break
    else:
        print("\nAPI still rate-limited. Waiting 5 minutes before next check...")
        print("-" * 60 + "\n")
        time.sleep(300)  # Wait 5 minutes
        attempt += 1
