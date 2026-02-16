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

**URL (spec):** `https://site.api.espn.com/apis/site/v2/sports/golf/pga/leaderboard`

### Important Discovery

**The dedicated `/leaderboard` endpoint returns 404.** Leaderboard data is actually contained within the **scoreboard endpoint** under `events[*].competitions[*].competitors[]`.

### Competitor Object Structure

Path: `events[*].competitions[*].competitors[*]`

```json
{
  "id": "string",           // Competitor ID (not athlete ID)
  "uid": "string",
  "type": "string",
  "order": "number",
  "athlete": {
    "fullName": "string",   // e.g., "Collin Morikawa"
    "displayName": "string", // e.g., "Collin Morikawa"
    "shortName": "string",   // e.g., "C. Morikawa"
    "flag": {
      "href": "string",
      "alt": "string",       // Country code, e.g., "USA"
      "rel": ["array"]
    }
  },
  "score": "string",         // Total score, e.g., "-22"
  "linescores": [
    {
      "value": "number",     // Round score relative to par
      "displayValue": "string", // e.g., "69"
      "period": "number",    // Round number (1-4)
      "linescores": [        // Hole-by-hole scores
        {
          "value": "number",
          "displayValue": "string",
          "period": "number", // Hole number
          "scoreType": {
            "displayValue": "string" // e.g., "Birdie", "Par"
          }
        }
      ],
      "statistics": {...}
    }
  ],
  "statistics": []
}
```

### Key Fields Identified

| Target Field | ESPN Path | Notes |
|--------------|-----------|-------|
| athlete_id | `competitors[*].id` | String, but need to verify if this is athleteId |
| display_name | `competitors[*].athlete.displayName` | Full name |
| short_name | `competitors[*].athlete.shortName` | "F. Lastname" format |
| position | **NOT FOUND** | Not explicitly present |
| total_score | `competitors[*].score` | String, e.g., "-22" |
| round_scores | `competitors[*].linescores[*].displayValue` | Per-round stroke total |
| thru_hole | **NOT FOUND** | May only appear during active rounds |
| status | **NOT FOUND** | No explicit field |

### Sample Athlete Data

| Athlete | ID | Display Name | Short Name | Total | R1 | R2 | R3 | R4 |
|---------|-----|--------------|------------|-------|-----|-----|-----|-----|
| Collin Morikawa | 10592 | Collin Morikawa | C. Morikawa | -22 | 69 | 68 | 62 | 67 |
| Min Woo Lee | 4410932 | Min Woo Lee | M. Lee | -21 | 67 | 65 | 70 | 65 |
| Scottie Scheffler | 9478 | Scottie Scheffler | S. Scheffler | -20 | 72 | 66 | 67 | 63 |
| Sepp Straka | 8961 | Sepp Straka | S. Straka | -21 | 66 | 66 | 67 | 68 |
| Hideki Matsuyama | 5860 | Hideki Matsuyama | H. Matsuyama | -18 | 67 | 67 | 67 | 69 |

### Athlete IDs Captured for Stats Calls

- **10592** - Collin Morikawa
- **9478** - Scottie Scheffler
- **5860** - Hideki Matsuyama

**Path to athlete IDs:** The ID in `competitors[*].id` appears to be the athlete ID based on values matching known ESPN athlete IDs.

### Player Name Format Observations

1. **No firstName/lastName split** - names provided only as complete strings
2. **displayName** = full name (e.g., "Collin Morikawa")
3. **shortName** = initial + last name (e.g., "C. Morikawa")
4. **No accents observed** in sampled names (but Sepp Straka has Austrian origins - ä may be normalized)

### Mapping to `current_leaderboard.json` Schema

| Target Schema Field | Source | Status |
|---------------------|--------|--------|
| athlete_id | `competitors[*].id` | Available |
| name | `competitors[*].athlete.displayName` | Available |
| position | - | NOT AVAILABLE (need to derive from sort order) |
| total_score | `competitors[*].score` | Available |
| round_1 | `competitors[*].linescores[0].displayValue` | Available |
| round_2 | `competitors[*].linescores[1].displayValue` | Available |
| round_3 | `competitors[*].linescores[2].displayValue` | Available |
| round_4 | `competitors[*].linescores[3].displayValue` | Available |
| thru | - | NOT AVAILABLE (completed tournament) |
| today | - | NOT AVAILABLE (completed tournament) |

### Event ID Parameter Testing

**Tested URLs:**
- `https://site.api.espn.com/apis/site/v2/sports/golf/pga/leaderboard?event=401811927` - **404**
- `https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard?event=401811927` - **Ignored** (returns current event instead)
- `https://site.api.espn.com/apis/site/v2/sports/golf/pga/summary?event=401811927` - **502**
- `https://site.api.espn.com/apis/site/v2/sports/golf/pga/events/401811927` - **404**

**Alternative Core API Endpoint:**
- `https://sports.core.api.espn.com/v2/sports/golf/leagues/pga/events/{eventId}/competitions/{eventId}/competitors`
- Returns paginated list with `$ref` links to detailed data
- For current event (401811932): 80 competitors, 4 pages, 25 per page
- Includes `movement` field (position change), `order` (leaderboard position), `amateur` flag
- Actual scoring data requires following `$ref` links

### Key Findings for Historical Data

1. **The scoreboard endpoint only returns the current/most recent event** - the `?event=` parameter is ignored
2. **The dedicated `/leaderboard` endpoint does not exist** (404)
3. **Historical event data** may require the core API (`sports.core.api.espn.com`) which uses `$ref` links
4. **For completed tournaments**, data may need to be captured and stored during/immediately after the event

### Recommendation

For the scraper implementation:
- **Current leaderboard:** Use `/scoreboard` endpoint - competitors data is embedded
- **Historical results:** May require alternate approach (scrape during event, or use core API with `$ref` dereferencing)

---

## 3. Player Stats Endpoint

*(To be completed in Task 4)*

---

## 4. Player Name Observations

*(To be completed in Task 5)*

---

## 5. Recommendations

*(To be completed in Task 6)*
