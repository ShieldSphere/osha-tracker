"""Test sorting options for the OSHA API."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
import time
from src.config import settings

client = httpx.Client(timeout=120.0, verify=False)
url = "https://apiprod.dol.gov/v4/get/OSHA/inspection/json"

# Try different sort parameters
sort_attempts = [
    {"sort": "-open_date"},  # Descending by open_date
    {"sort": "-load_dt"},    # Descending by load_dt
    {"orderby": "open_date desc"},
    {"order": "-open_date"},
    {"sortby": "open_date", "sortdir": "desc"},
]

base_params = {"X-API-KEY": settings.DOL_API_KEY, "limit": "5"}

for i, sort_params in enumerate(sort_attempts):
    print(f"\nAttempt {i+1}: Testing {sort_params}")
    params = {**base_params, **sort_params}

    time.sleep(2)  # Rate limit protection

    response = client.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        records = data.get("data", [])
        if records:
            print(f"  Success! First record open_date: {records[0].get('open_date', 'N/A')}")
            print(f"  First record load_dt: {records[0].get('load_dt', 'N/A')}")
        else:
            print("  Got 0 records")
    elif response.status_code == 400:
        # Check if the error is about invalid parameter or just ignored
        print(f"  Error 400: {response.text[:100]}")
    elif response.status_code == 429:
        print("  Rate limited - wait a minute and try again")
        break
    else:
        print(f"  Status {response.status_code}: {response.text[:100]}")

client.close()
print("\nDone testing sort options.")
