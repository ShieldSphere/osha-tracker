import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from datetime import datetime, timedelta
from src.services.osha_client import OSHAClient

async def test_sync():
    """Test OSHA API sync to see recent inspections."""
    client = OSHAClient()

    print("=" * 60)
    print("Testing OSHA API - Fetching recent inspections")
    print("=" * 60)

    # Fetch first batch to see what we get
    print("\n1. Fetching first 10 records...")
    try:
        records = await client.fetch_inspections(limit=10, offset=0)
        print(f"   ✓ Fetched {len(records)} records")

        if records:
            first = records[0]
            print(f"\n2. Sample record fields:")
            print(f"   - activity_nr: {first.get('activity_nr')}")
            print(f"   - estab_name: {first.get('estab_name')}")
            print(f"   - open_date: {first.get('open_date')}")
            print(f"   - load_dt: {first.get('load_dt')}")
            print(f"   - site_state: {first.get('site_state')}")

            # Check load_dt dates
            print(f"\n3. Checking load_dt dates in first 10 records:")
            for i, record in enumerate(records):
                load_dt_str = record.get('load_dt')
                if load_dt_str:
                    try:
                        load_dt = datetime.strptime(str(load_dt_str)[:19], "%Y-%m-%dT%H:%M:%S")
                        days_ago = (datetime.now() - load_dt).days
                        print(f"   [{i+1}] {record.get('activity_nr')} - {load_dt} ({days_ago} days ago)")
                    except:
                        print(f"   [{i+1}] {record.get('activity_nr')} - Invalid date: {load_dt_str}")
                else:
                    print(f"   [{i+1}] {record.get('activity_nr')} - No load_dt")

            # Now test the recent sync function
            print(f"\n4. Testing fetch_all_recent_inspections (last 3 days)...")
            recent = await client.fetch_all_recent_inspections(days_back=3, batch_size=200, max_records=1000)
            print(f"   ✓ Found {len(recent)} inspections loaded in last 3 days")

            if recent:
                print(f"\n5. Sample recent inspections:")
                for i, record in enumerate(recent[:5]):
                    load_dt = record.get('load_dt')
                    print(f"   [{i+1}] {record.get('activity_nr')} - {record.get('estab_name')} - {load_dt}")
            else:
                print("\n   ⚠ No recent inspections found!")
                print("   This could mean:")
                print("   - OSHA hasn't published any inspections in the last 3 days")
                print("   - The load_dt field is not being updated")
                print("   - The API is returning old data first")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_sync())
