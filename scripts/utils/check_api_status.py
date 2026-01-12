"""Check if the OSHA API is accessible."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
import time
from src.config import settings

def check_api_status():
    """Check if the OSHA API is accessible (not rate-limited)."""
    url = "https://apiprod.dol.gov/v4/get/OSHA/inspection/json"
    params = {
        "X-API-KEY": settings.DOL_API_KEY,
        "limit": 1,  # Just get 1 record to test
        "offset": 0
    }

    print("Checking OSHA API status...")
    print(f"URL: {url}")
    print(f"Requesting 1 record to test connectivity...\n")

    try:
        with httpx.Client(timeout=30.0, verify=False) as client:
            response = client.get(url, params=params)

            if response.status_code == 200:
                data = response.json().get('data', [])
                print(f"[OK] API is accessible!")
                print(f"  Status: {response.status_code}")
                print(f"  Records returned: {len(data)}")
                if data:
                    print(f"\n  Sample record:")
                    sample = data[0]
                    print(f"    activity_nr: {sample.get('activity_nr')}")
                    print(f"    estab_name: {sample.get('estab_name')}")
                    print(f"    open_date: {sample.get('open_date')}")
                    print(f"    load_dt: {sample.get('load_dt')}")
                return True
            elif response.status_code == 429:
                print(f"[RATE LIMITED] API is rate-limited")
                print(f"  Status: {response.status_code}")
                print(f"  Message: Too many requests")
                print(f"\n  You'll need to wait before making more requests.")
                print(f"  The DOL OSHA API has rate limits to prevent abuse.")
                return False
            else:
                print(f"[ERROR] API returned unexpected status: {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                return False

    except Exception as e:
        print(f"[ERROR] Error connecting to API: {e}")
        return False

if __name__ == "__main__":
    check_api_status()
