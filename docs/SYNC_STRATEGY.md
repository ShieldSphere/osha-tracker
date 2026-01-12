# OSHA Tracker - Violation Sync Strategy

## Overview

This document explains the smart sync strategy for tracking new OSHA violations as they're issued - critical for lead generation timing.

## The Challenge

**OSHA's citation delay**: Citations are typically issued **3-9 months** after an inspection is conducted. This means:
- An inspection happens today
- No violations appear in the database immediately
- 6 months later, citations are issued and violations appear
- **You need to catch these NEW violations quickly for timely outreach**

## The Solution

### Two-Tier Sync Architecture

#### 1. Inspection Sync (`sync_service.py`)
**Purpose**: Keep up with NEW inspections

**Schedule**:
- Every 1 hour (configurable via `FETCH_INTERVAL_HOURS`)
- Daily at 2 AM for full sync

**What it does**:
- Fetches recent inspections from OSHA API
- Creates new inspection records
- Updates existing inspection metadata
- Does NOT fetch violations (too slow, rate-limited)

#### 2. Violation Sync (`violation_sync_service.py`) ⭐ **KEY FOR LEAD GENERATION**
**Purpose**: Watch existing inspections for NEW violations appearing

**Schedule**:
- Every 4 hours
- Daily at 3 AM (after inspection sync)

**Smart Strategy**:
```
Priority 1: Inspections opened 3-9 months ago WITH NO violations yet
└─ These are in the citation window - highest chance of NEW violations

Priority 2: Inspections WITH violations but case not closed
└─ Might get additional violations added

Priority 3: Recently checked inspections (backfill)
└─ Fill remaining API quota checking other recent inspections
```

**Rate Limiting**:
- Checks max 100 inspections per run (configurable)
- 1.2 second delay between API calls
- Avoids OSHA API rate limits (429 errors)

## Database Schema

### Inspection Model - New Fields
```python
# Violation sync tracking
last_violation_check: DateTime     # When we last checked for violations
violation_check_count: int         # How many times we've checked
```

### Violation Model
```python
# Unique constraint on (activity_nr, citation_id)
# Prevents duplicate violations
# Tracks issuance_date, penalties, violation type, etc.
```

## How It Works - Step by Step

### Day 0: Inspection Occurs
```
1. OSHA conducts inspection at "ABC Construction Co"
2. Inspection sync picks it up within 1 hour
3. Inspection record created (no violations yet)
```

### Day 1-90: Waiting Period
```
1. Violation sync checks the inspection every 4 hours
2. No violations found yet (expected)
3. last_violation_check updated each time
```

### Day 180: Citation Issued! 🎯
```
1. OSHA issues citations for violations
2. Violation sync checks within 4 hours
3. NEW violations detected!
4. Violations created in database
5. Inspection penalties updated
6. ✨ TRIGGER: This is when you reach out!
```

## API Endpoints

### Manual Violation Sync
```http
POST /api/inspections/sync/violations?max_inspections=100
```
Returns statistics about new violations found.

### Sync Violations for Single Inspection
```http
POST /api/inspections/{inspection_id}/sync-violations
```
On-demand check for a specific inspection.

## Lead Generation Workflow

### 1. Monitor for New Violations
```sql
SELECT i.*, COUNT(v.id) as violation_count
FROM inspections i
JOIN violations v ON v.activity_nr = i.activity_nr
WHERE v.created_at >= NOW() - INTERVAL '4 hours'
GROUP BY i.id
ORDER BY v.created_at DESC
```

### 2. Alert/Notification System (TODO)
When new violations are detected:
- Send email alert
- Create task in CRM
- Update dashboard with "NEW" badge
- Trigger enrichment workflow

### 3. Enrich & Contact
1. Run web enrichment on the company
2. Get contact info, LinkedIn profiles
3. Reach out while citation is fresh (6-month window)

## Configuration

### Environment Variables
```env
# Inspection sync frequency
FETCH_INTERVAL_HOURS=1

# API credentials
DOL_API_KEY=your_key_here
```

### Scheduler Settings
Located in `src/services/scheduler.py`:

```python
# Inspection sync
IntervalTrigger(hours=1)      # Every hour
CronTrigger(hour=2)           # Daily at 2 AM

# Violation sync - THE KEY
IntervalTrigger(hours=4)      # Every 4 hours
CronTrigger(hour=3)           # Daily at 3 AM
```

## Performance Metrics

### API Rate Limits
- OSHA API: ~500 requests/hour (unofficial limit)
- With 1.2s delay: 50 requests/minute = 3000/hour
- Checking 100 inspections/run = 100 requests
- Running every 4 hours = 600 requests/day (well under limit)

### Expected Violations Per Day
Based on typical OSHA citation rates:
- ~30% of inspections result in violations
- Checking 100 inspections every 4 hours
- Expect to find 5-10 new violations per day

## CSV Bulk Load Strategy

Since you've loaded historical data via CSV:

### 1. Initial CSV Load (Done)
```
✓ Loaded inspections back to 2024
✓ Loaded violations from CSV
✓ Historical data complete
```

### 2. Going Forward (Automated)
```
✓ New inspections: API sync (hourly)
✓ New violations: Smart sync (every 4h)
✓ No more CSV needed
```

### 3. Gap Filling (Optional)
If you need to check old inspections for late violations:
```python
# One-time backfill
await violation_sync_service.sync_violations_smart(
    max_inspections_to_check=500  # Higher limit for backfill
)
```

## Monitoring & Logs

### Check Sync Status
```python
# Last sync info
GET /api/inspections/sync/status

# Response:
{
    "total_inspections": 15000,
    "last_sync": "2026-01-08T18:00:00",
    "oldest_inspection": "2024-01-01",
    "newest_inspection": "2026-01-08"
}
```

### View Scheduled Jobs
```python
from src.services.scheduler import get_scheduled_jobs

jobs = get_scheduled_jobs()
# Shows: next_run_time for each job
```

### Log Messages to Watch For
```
✓ "Found X NEW violations for {company}"
  └─ This is your lead generation trigger!

⚠ "Rate limited by API, waiting 60 seconds..."
  └─ Adjust max_inspections or delay

✓ "Violation sync completed: found {X} new violations"
  └─ Your daily new leads count
```

## Optimization Tips

### If You're Getting Rate Limited
1. Reduce `max_inspections_to_check` from 100 to 50
2. Increase `rate_limit_delay` from 1.2s to 2.0s
3. Run sync less frequently (every 6h instead of 4h)

### If You Want More Coverage
1. Increase `max_inspections_to_check` to 200
2. Run sync more frequently (every 2h)
3. Add more priority tiers for older inspections

### For Specific States/Industries
Modify the candidate selection query to filter by:
```python
.where(and_(
    Inspection.site_state.in_(['CA', 'TX', 'FL']),
    Inspection.naics_code.like('23%')  # Construction
))
```

## Future Enhancements

### 1. Webhook Notifications
When new violations found:
- POST to Slack/Discord webhook
- Email alert to sales team
- SMS notification

### 2. Smart Enrichment Trigger
Auto-enrich companies when new violations appear:
```python
if new_violations_found > 0:
    await enrich_company(inspection.id)
```

### 3. Violation Alert Dashboard
Build a "New Violations" view showing:
- Violations found in last 24 hours
- Company info pre-enriched
- One-click contact action

### 4. ML-Based Prioritization
Train a model to predict which inspections are most likely to get violations:
- Industry (construction has higher rates)
- Prior violation history
- Inspection scope/type
- Regional patterns

## Summary

**The Key Insight**:
OSHA's 6-month citation delay means you can't just sync new inspections. You must actively **monitor existing inspections** for violations appearing months later. The violation sync service implements a smart prioritization strategy to catch these NEW violations quickly while staying within API rate limits.

**Your Lead Generation Window**:
1. Violation issued (you detect within 4 hours)
2. Company has ~90 days to contest or abate
3. Window to reach out and offer services
4. Act fast before competitors see the public citation!
