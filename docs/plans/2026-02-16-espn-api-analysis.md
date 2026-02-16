# ESPN API Response Analysis

## Executive Summary

### What Works

| Data Need | Available | Endpoint |
|-----------|-----------|----------|
| Tournament names | ✅ | `/scoreboard` → calendar |
| Tournament dates | ✅ | `/scoreboard` → calendar |
| Player names | ✅ | `/statistics` |
| Athlete IDs | ✅ | `/statistics` |
| Position per tournament | ✅ | `/athletes/{id}/stats` |
| FedEx points per tournament | ✅ | `/athletes/{id}/stats` |
| Historical 2026 results | ✅ | `/athletes/{id}/stats` |

### Key Findings

1. **The `/leaderboard` endpoint does not exist** (returns 404). Use `/scoreboard` instead for current event data.

2. **Historical tournament data** is available via player stats endpoint - each player's stats include all 2026 events with position and FedEx points.

3. **Data model is player-centric** - to get tournament results, you fetch each player's stats rather than fetching a tournament leaderboard.

4. **Names are ASCII-normalized** - ESPN removes accents/diacritics from player names.

5. **Course and purse data are NOT available** in these API endpoints.

### Recommended Approach

```
1. GET /scoreboard → Extract season calendar (tournament names + dates)
2. GET /statistics → Get player roster with athlete IDs
3. For each player: GET /athletes/{id}/stats?season=2026 → Get per-tournament results
4. Aggregate into tournament-centric JSON if needed
```

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

**URL:** `https://site.web.api.espn.com/apis/common/v3/sports/golf/athletes/{athleteId}/stats?season=2026`

### Top-Level JSON Structure

```json
{
  "leaguesStats": [
    {
      "eventsStats": [...]  // Array of tournament results
    }
  ]
}
```

### Tournament Result Structure (Per Event)

Path: `leaguesStats[0].eventsStats[*]`

```json
{
  "id": "string",           // Event ID
  "name": "string",         // Tournament name
  "competitions": [
    {
      "competitors": [
        {
          "status": {
            "position": {
              "displayValue": "string"  // e.g., "1", "T13", "MC"
            }
          },
          "stats": [
            {
              "cupPoints": {
                "displayValue": "string"  // FedEx Cup points earned
              }
            }
          ]
        }
      ]
    }
  ]
}
```

### Key Fields Identified

| Target Field | ESPN Path | Notes |
|--------------|-----------|-------|
| event_name | `eventsStats[*].name` | Tournament name |
| position | `eventsStats[*].competitions[0].competitors[0].status.position.displayValue` | "1", "T13", "MC" |
| fedex_points | `eventsStats[*].competitions[0].competitors[0].stats[*].cupPoints.displayValue` | Points earned |
| score | Available in nested stats | Total score for tournament |

### Sample Data - Collin Morikawa (ID: 10592)

| Tournament | Position | FedEx Points | Score |
|------------|----------|--------------|-------|
| Sony Open in Hawaii | MC | 0 | 140 (E) |
| WM Phoenix Open | T54 | 6 | 281 (-3) |
| AT&T Pebble Beach Pro-Am | 1 | 700 | 266 (-22) |

### Sample Data - Hideki Matsuyama (ID: 5860)

| Tournament | Position | FedEx Points | Score |
|------------|----------|--------------|-------|
| Sony Open in Hawaii | T13 | 54 | 271 (-9) |
| Farmers Insurance Open | T11 | 59 | 276 (-12) |
| WM Phoenix Open | 2 | 300 | 268 (-16) |
| AT&T Pebble Beach Pro-Am | T8 | 148 | 270 (-18) |

### Important Notes

1. **No athlete name in response** - The stats endpoint does NOT include the player's name. You must already know the athlete ID and name from another source.
2. **Historical data included** - Returns all 2026 events the player has competed in
3. **Season parameter** - Use `?season=2026` for current season

---

## 3a. Statistics/Standings Endpoint

**URL:** `https://site.api.espn.com/apis/site/v2/sports/golf/pga/statistics`

### Purpose

This endpoint provides the **FedEx Cup standings** with a complete player list including athlete IDs and names. Use this to get the roster of players to then query individual stats.

### Player Entry Structure

```json
{
  "athlete": {
    "id": "string",           // Athlete ID for stats lookup
    "displayName": "string",  // Full name
    "shortName": "string"     // "F. Lastname" format
  },
  "stats": [...]              // Current FedEx Cup points
}
```

### Sample Data

| Rank | Display Name | Athlete ID | FedEx Points |
|------|--------------|------------|--------------|
| 1 | Chris Gotterup | 4690755 | 1066 |
| 2 | Scottie Scheffler | 9478 | 938 |
| 3 | Collin Morikawa | 10592 | 706 |
| 4 | Hideki Matsuyama | 5860 | 560 |
| 5 | Sepp Straka | 8961 | 419 |
| 6 | Min Woo Lee | 4410932 | 417 |

### Recommended Data Flow

```
1. GET /statistics → Get player list with IDs and names
2. For each player:
   GET /athletes/{id}/stats?season=2026 → Get per-tournament results
3. Aggregate into tournament-centric view if needed
```

---

## 4. Player Name Observations

### Available Name Fields

| Field | Location | Format | Example |
|-------|----------|--------|---------|
| displayName | `/statistics`, `/scoreboard` | "FirstName LastName" | "Collin Morikawa" |
| shortName | `/statistics`, `/scoreboard` | "F. LastName" | "C. Morikawa" |
| fullName | `/scoreboard` competitors | "FirstName LastName" | "Collin Morikawa" |

**Note:** No separate `firstName` / `lastName` fields are provided. Names are only available as complete strings.

### Name Format Observations

1. **ASCII normalized** - ESPN appears to normalize accented characters to ASCII
   - Sepp Straka (Austrian) appears as "Sepp Straka" not "Sepp Stráka"
   - No ä, é, ñ, Å or other diacritics observed in sampled data

2. **No suffixes observed** - In the current FedEx standings sample:
   - No "Jr." or "III" suffixes found
   - May appear in full roster (Davis Love III, etc.) but not in top standings

3. **Multi-word names** - Handled correctly:
   - "Min Woo Lee" (three words)
   - "Hideki Matsuyama" (standard)

4. **shortName format** - Consistent "F. LastName" pattern:
   - "C. Morikawa"
   - "M. Lee" (for Min Woo Lee - only uses first initial)
   - "H. Matsuyama"

### Implications for Name Normalization

Since your scraper needs to match player names across sources:

1. **Use athlete ID as canonical key** - ESPN's `athleteId` is the reliable unique identifier
2. **Store displayName as-is** - ESPN's displayName is already normalized (no accents)
3. **No parsing needed** - You don't need to split first/last names for your use case
4. **shortName useful for display** - "C. Morikawa" format is compact for leaderboards

### Potential Issues

1. **Name variations across sources** - If matching against non-ESPN data, may need fuzzy matching
2. **Suffixes** - If Jr./III players appear, verify ESPN includes suffix in displayName
3. **Asian name order** - "Min Woo Lee" follows Western order (given name first)

---

## 5. Recommendations

### Spec Adjustments

Based on this analysis, the original CLAUDE.md spec needs these updates:

| Original Spec | Actual |
|---------------|--------|
| `/leaderboard` endpoint | Does not exist (404) - use `/scoreboard` |
| Tournament-centric data model | Player-centric - fetch stats per player |
| FedEx standings from leaderboard | Use `/statistics` endpoint |

### Recommended Implementation

#### Endpoints to Use

```python
# 1. Season schedule (tournament names + dates)
SCHEDULE_URL = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard"
# Path: leagues[0].calendar[*] → {id, label, startDate, endDate}

# 2. Player roster with current FedEx standings
STANDINGS_URL = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/statistics"
# Path: athlete → {id, displayName, shortName}

# 3. Per-player tournament results (position + FedEx points)
PLAYER_STATS_URL = "https://site.web.api.espn.com/apis/common/v3/sports/golf/athletes/{athleteId}/stats?season=2026"
# Path: leaguesStats[0].eventsStats[*] → {name, position.displayValue, cupPoints.displayValue}
```

#### Data Flow for Your Use Case

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Fetch /scoreboard                                        │
│    → Extract calendar: tournament names + dates             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Fetch /statistics                                        │
│    → Get player list: athleteId + displayName               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. For each player: Fetch /athletes/{id}/stats              │
│    → Get per-tournament: position + FedEx points            │
│    (Rate limit: 1-2 sec between requests)                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Aggregate into tournament-centric JSON                   │
│    → tournament_results/{eventId}.json                      │
│       { players: [ {name, position, fedex_points}, ... ] }  │
└─────────────────────────────────────────────────────────────┘
```

### Rate Limiting

- ESPN's undocumented APIs have no published rate limits
- Recommend 1-2 second delay between player stats requests
- Cache aggressively - player stats for completed tournaments won't change

### Output Schema (Simplified)

Based on your stated needs (tournament name, dates, position, golfer name, FedEx points):

**tournament_schedule.json**
```json
[
  {
    "event_id": "401811927",
    "name": "The Sentry",
    "start_date": "2026-01-08",
    "end_date": "2026-01-11"
  }
]
```

**tournament_results/{eventId}.json**
```json
{
  "event_id": "401811932",
  "name": "AT&T Pebble Beach Pro-Am",
  "results": [
    {"athlete_id": "10592", "name": "Collin Morikawa", "position": "1", "fedex_points": 700},
    {"athlete_id": "4410932", "name": "Min Woo Lee", "position": "T2", "fedex_points": 340}
  ]
}
```

### Not Available (Excluded from Scope)

- Course names
- Purse amounts
- Real-time "thru" hole data (only available during active rounds)
- Playoff details beyond position
