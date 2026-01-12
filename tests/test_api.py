"""Test to check date distribution in OSHA inspection data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
import time
from collections import Counter

from src.config import settings

print(f"API Key loaded: {settings.DOL_API_KEY[:10]}..." if settings.DOL_API_KEY else "NO API KEY!")
print()

client = httpx.Client(timeout=120.0, verify=False)

url = "https://apiprod.dol.gov/v4/get/OSHA/inspection/json"
params = {"X-API-KEY": settings.DOL_API_KEY, "limit": "50"}  # Smaller batch

print("Fetching 50 inspection records to check date distribution...")
print("(Using smaller batch to avoid rate limiting)")
print()

# Wait a moment before request in case we were just rate limited
time.sleep(2)

response = client.get(url, params=params)

if response.status_code == 200:
    data = response.json()
    records = data.get("data", [])

    print(f"Got {len(records)} records")
    print()

    # Check open_date distribution
    years = Counter()
    recent = []  # 2024-2026

    for r in records:
        open_date = r.get("open_date", "")
        if open_date:
            year = open_date[:4]
            years[year] += 1
            if year in ("2024", "2025", "2026"):
                recent.append({
                    "activity_nr": r.get("activity_nr"),
                    "estab_name": r.get("estab_name"),
                    "open_date": open_date,
                    "site_state": r.get("site_state"),
                })

    print("Open dates by year:")
    for year, count in sorted(years.items()):
        print(f"  {year}: {count}")

    print()
    print(f"Recent inspections (2024+): {len(recent)}")
    for r in recent[:10]:
        print(f"  {r['open_date'][:10]} - {r['estab_name'][:40]} ({r['site_state']})")

elif response.status_code == 429:
    print("Rate limited (429). Wait a minute and try again.")
    print("The DOL API has rate limits - we need to slow down requests.")
else:
    print(f"Error: {response.status_code} - {response.text[:200]}")

client.close()
