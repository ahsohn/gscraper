# ESPN API Response Analysis

## Executive Summary

*(To be completed in Task 6)*

---

## 1. Scoreboard Endpoint

**URL:** `https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard`

### Top-Level JSON Structure

```json
{
  "leagues": [array],    // League metadata and full season calendar
  "season": {object},    // Current season info
  "day": {object},       // Current day info
  "events": [array]      // Active/recent event details with scoring
}
```

### Key Fields Identified

| Target Field | ESPN Path | Notes |
|--------------|-----------|-------|
| event_id | `leagues[0].calendar[*].id` or `events[*].id` | String format, e.g., "401811927" |
| name | `leagues[0].calendar[*].label` or `events[*].name` | Full tournament name |
| dates | `leagues[0].calendar[*].startDate` / `endDate` | ISO 8601 format |
| course | *NOT FOUND* | Not present in scoreboard response |
| purse | *NOT FOUND* | Not present in scoreboard response |
| status | *NOT FOUND* | No explicit status field |

### Detailed Structure

**Leagues Array:**
- `leagues[0].id` - league ID string
- `leagues[0].name` - "PGA TOUR"
- `leagues[0].abbreviation` - "PGA"
- `leagues[0].season.year` - season year (2026)
- `leagues[0].calendar[]` - array of 41 tournament entries

**Calendar Entry Structure:**
```json
{
  "id": "401811927",
  "label": "The Sentry",
  "startDate": "2026-01-08T00:00:00Z",
  "endDate": "2026-01-11T00:00:00Z",
  "event": { "$ref": "..." }
}
```

**Events Array (Active Tournaments):**
- `events[*].id` - event ID
- `events[*].name` - tournament name
- `events[*].date` / `events[*].endDate` - timestamps
- `events[*].competitions[*].competitors[]` - player scoring data
- `events[*].competitions[*].competitors[*].linescores[]` - round-by-round scores

### Data Observations

1. **41 events** in the 2026 season calendar
2. **Event IDs** range from 401811927 to 401850982
3. **Date range:** 2026-01-08 through 2026-12-06
4. **Missing data:** Course names, purse amounts, and tournament status are NOT in this endpoint

### Event ID for Subsequent Calls

**Event ID captured:** `401811927` (The Sentry - season opener)

**Path to event IDs:** `leagues[0].calendar[*].id`

### Mapping to `tournament_schedule.json` Schema

| Target Schema Field | Source | Status |
|---------------------|--------|--------|
| event_id | `calendar[*].id` | Available |
| name | `calendar[*].label` | Available |
| start_date | `calendar[*].startDate` | Available |
| end_date | `calendar[*].endDate` | Available |
| course | - | NOT AVAILABLE |
| purse | - | NOT AVAILABLE |
| status | - | NOT AVAILABLE |

**Note:** May need alternate endpoint or enrichment for course/purse/status data.

---

## 2. Leaderboard Endpoint

*(To be completed in Task 2)*

---

## 3. Player Stats Endpoint

*(To be completed in Task 4)*

---

## 4. Player Name Observations

*(To be completed in Task 5)*

---

## 5. Recommendations

*(To be completed in Task 6)*
