# OSHA Tracker Data Strategy

## Focus: Recent Data (2020+)

The application focuses on inspections from **2020 onwards** for the following reasons:
1. **Lead Generation**: Recent inspections are more relevant for sales outreach
2. **Database Performance**: Keeps database size manageable (~20K inspections vs 100K+)
3. **API Efficiency**: Reduces unnecessary API calls for old data
4. **Data Quality**: Recent data is more accurate and actionable

## Current Database Status

**After Cleanup (Jan 9, 2026):**
- **Total Inspections**: 20,082
- **Total Violations**: 8,406
- **Date Range**: Feb 24, 2023 to Jan 5, 2026 (2.9 years)
- **Database Size**: 22 MB
- **Main Tables**:
  - Inspections: 8.8 MB
  - Violations: 3.0 MB

### Breakdown by Year:
- 2023: 836
- 2024: 10,164
- 2025: 9,071
- 2026: 11

## Sync Strategy

### What Gets Synced:
- ✅ Inspections opened in 2020 or later
- ✅ All violations for those inspections
- ✅ New inspections published to OSHA (detected by `load_dt`)
- ❌ Inspections opened before 2020 (automatically filtered)

### Sync Frequency:
- **Inspections**: Every 3 hours + daily at 2 AM
- **Violations**: Every 6 hours + daily at 3 AM

### Rate Limiting:
- 3 seconds between API requests (20 requests/minute)
- 2 minute wait + retry when rate limited
- Conservative batch sizes (100 records per request, max 5,000 per sync)

## Data Maintenance

### Automatic Filters:
The sync service now **automatically rejects** inspections opened before 2020. This is implemented in `src/services/sync_service.py`:

```python
# Filter: Only accept inspections from 2020 onwards
open_date = parsed.get("open_date")
if open_date and open_date.year < 2020:
    logger.debug(f"Skipping inspection {activity_nr} - too old ({open_date.year})")
    return False, False
```

### Manual Cleanup:
If old data somehow gets into the database, use the cleanup script:

```bash
python cleanup_old_data.py
```

This will:
1. Find all inspections opened before 2020
2. Count related violations
3. Show breakdown by year
4. Confirm before deletion
5. Delete violations first (foreign key constraint)
6. Delete old inspections
7. Show remaining data summary

### Database Monitoring:
Check database size and health:

```bash
python check_database_size.py
```

This shows:
- Record counts
- Date range and span
- Breakdown by year
- Table sizes
- Total database size
- Data quality checks (missing dates, old data, etc.)

## Performance Considerations

### Current Performance:
- 22 MB database is very small and fast
- Even at 100K inspections, database would be ~100 MB (still very manageable)
- PostgreSQL handles millions of rows easily

### Indexes:
Key indexes for performance:
- `activity_nr` (primary lookup)
- `open_date` (date filtering, sorting)
- `site_state` (state filtering)
- `estab_name` (search)
- `load_dt` (sync detection)

### Query Optimization:
- Dashboard queries use indexed fields
- Pagination limits result sets
- Filters applied at database level (not in Python)

## Expected Growth

With 2020+ focus:
- **Current**: ~20K inspections
- **Expected annual growth**: ~10K inspections per year
- **5-year projection**: ~50K inspections (~50 MB)
- **10-year projection**: ~100K inspections (~100 MB)

This is very manageable for PostgreSQL/Supabase.

## Why 2020 as the Cutoff?

1. **COVID Impact**: 2020 marks a significant shift in workplace safety (COVID-19)
2. **Relevance**: Companies care about their recent inspection history
3. **Statute of Limitations**: Most OSHA citations have 5-7 year limits
4. **Data Quality**: Recent data is more complete and accurate
5. **Lead Value**: Recent violations = hot leads

## Migration Path

If you ever need older data:
1. Adjust the cutoff year in `sync_service.py` (line 94)
2. Re-run sync to fetch older inspections
3. Monitor database size with `check_database_size.py`
4. Consider archiving if database exceeds 100 MB

## Best Practices

✅ **Do:**
- Run `check_database_size.py` monthly to monitor growth
- Review sync logs for "skipped (pre-2020)" counts
- Keep the 2020+ focus unless there's a specific need

❌ **Don't:**
- Manually import old CSV data without date filtering
- Remove the 2020 filter without considering database size
- Ignore database size warnings

## Troubleshooting

### "Database is getting too large"
1. Run `check_database_size.py` to identify the issue
2. Check for duplicate data or test data
3. Consider adjusting date cutoff if needed
4. Run `cleanup_old_data.py` to remove pre-2020 data

### "Not enough data for analysis"
1. Check date range with `check_database_size.py`
2. Verify sync is running (check scheduler logs)
3. Check API rate limit status with `check_api_status.py`
4. If needed, adjust cutoff year in sync service

### "Queries are slow"
1. Check database size with `check_database_size.py`
2. Verify indexes exist on key fields
3. Check for missing `WHERE` clauses in queries
4. Consider adding pagination to large result sets
