# ESPN API Exploration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Explore ESPN's undocumented PGA golf API endpoints and document actual response structures for building parsers.

**Architecture:** Browser-based fetching of three ESPN endpoints (scoreboard, leaderboard, player stats), capturing JSON responses, analyzing structures, and documenting findings with mappings to target schemas.

**Tech Stack:** WebFetch tool for API calls, markdown for documentation

---

### Task 1: Fetch and Analyze Scoreboard Endpoint

**Files:**
- Create: `docs/plans/2026-02-16-espn-api-analysis.md` (initial structure)

**Step 1: Fetch the scoreboard endpoint**

Use WebFetch to call: `https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard`

Prompt: "Return the complete JSON structure. List all top-level keys and their types. For nested objects, show the structure 2-3 levels deep. Identify: event IDs, tournament names, dates, course names, purse amounts, tournament status."

**Step 2: Create analysis document with scoreboard findings**

Create `docs/plans/2026-02-16-espn-api-analysis.md` with:
- Executive Summary section (placeholder)
- Scoreboard Endpoint section with:
  - Full URL
  - Top-level JSON structure
  - Key fields identified (event_id location, name, dates, course, purse, status)
  - Mapping to `tournament_schedule.json` schema from spec
  - Any unexpected fields or missing data

**Step 3: Extract event ID and athlete ID for subsequent calls**

From the scoreboard response, note:
- One active/recent event ID (for leaderboard call)
- Document the path to access event IDs in the JSON

**Step 4: Commit**

```bash
git add docs/plans/2026-02-16-espn-api-analysis.md
git commit -m "docs: add scoreboard endpoint analysis"
```

---

### Task 2: Fetch and Analyze Leaderboard Endpoint (Current Tournament)

**Files:**
- Modify: `docs/plans/2026-02-16-espn-api-analysis.md`

**Step 1: Fetch the leaderboard endpoint (no params)**

Use WebFetch to call: `https://site.api.espn.com/apis/site/v2/sports/golf/pga/leaderboard`

Prompt: "Return the complete JSON structure. List all top-level keys. For the players/competitors array, show the full structure of one player object including: name fields, athlete ID, position, scores (total, per-round, today), thru hole, status. Note any name variations or accent characters."

**Step 2: Document leaderboard structure**

Add to analysis doc:
- Leaderboard Endpoint section with:
  - Full URL
  - Top-level JSON structure
  - Player object structure (exact field names and paths)
  - Mapping to `current_leaderboard.json` schema from spec
  - Player name format observations (accents, suffixes, etc.)

**Step 3: Extract athlete IDs for player stats call**

From the leaderboard response, note:
- 2-3 athlete IDs (preferably players with different name formats)
- Document the path to access athlete IDs in the JSON

**Step 4: Commit**

```bash
git add docs/plans/2026-02-16-espn-api-analysis.md
git commit -m "docs: add leaderboard endpoint analysis"
```

---

### Task 3: Fetch Leaderboard with Event ID Parameter

**Files:**
- Modify: `docs/plans/2026-02-16-espn-api-analysis.md`

**Step 1: Fetch leaderboard for specific event**

Use WebFetch to call: `https://site.api.espn.com/apis/site/v2/sports/golf/pga/leaderboard?event={eventId}`
(Use event ID captured from Task 1)

Prompt: "Compare this response structure to the current leaderboard. Note any differences. Confirm the event ID parameter works for historical data. Check if completed tournament data includes final positions and all round scores."

**Step 2: Document event-specific leaderboard findings**

Add to Leaderboard section:
- Event ID parameter usage
- Any structural differences from current leaderboard
- Confirmation that historical data is accessible
- Notes on completed vs in-progress tournament data

**Step 3: Commit**

```bash
git add docs/plans/2026-02-16-espn-api-analysis.md
git commit -m "docs: add event-specific leaderboard analysis"
```

---

### Task 4: Fetch and Analyze Player Stats Endpoint

**Files:**
- Modify: `docs/plans/2026-02-16-espn-api-analysis.md`

**Step 1: Fetch player stats endpoint**

Use WebFetch to call: `https://site.web.api.espn.com/apis/common/v3/sports/golf/athletes/{athleteId}/stats?season=2026`
(Use athlete ID captured from Task 2)

Prompt: "Return the complete JSON structure. Identify: FedEx Cup points (exact field name and path), earnings, events played, wins, top 10s, scoring average. Note the season parameter behavior."

**Step 2: Document player stats structure**

Add to analysis doc:
- Player Stats Endpoint section with:
  - Full URL pattern
  - Top-level JSON structure
  - FedEx Cup points location (critical field)
  - All stats fields available
  - Mapping to `fedex_standings.json` schema from spec

**Step 3: Test with second athlete ID**

Fetch stats for a different athlete to confirm structure consistency.

**Step 4: Commit**

```bash
git add docs/plans/2026-02-16-espn-api-analysis.md
git commit -m "docs: add player stats endpoint analysis"
```

---

### Task 5: Document Player Name Observations

**Files:**
- Modify: `docs/plans/2026-02-16-espn-api-analysis.md`

**Step 1: Compile name examples from responses**

Review all fetched data for player name examples showing:
- Accent marks (Åberg, Niemann, etc.)
- Suffixes (III, Jr.)
- Multiple name formats for same player
- Short name vs display name vs full name fields

**Step 2: Add Player Name Observations section**

Document:
- Which fields contain player names
- Format differences between fields
- Examples of problematic names
- Recommendations for normalization approach

**Step 3: Commit**

```bash
git add docs/plans/2026-02-16-espn-api-analysis.md
git commit -m "docs: add player name observations"
```

---

### Task 6: Write Executive Summary and Recommendations

**Files:**
- Modify: `docs/plans/2026-02-16-espn-api-analysis.md`

**Step 1: Write Executive Summary**

Summarize:
- Which endpoints work as expected
- Key surprises or deviations from spec
- Data completeness assessment
- Any rate limiting or caching headers observed

**Step 2: Write Recommendations section**

Document:
- Spec adjustments needed (if any)
- Parser implementation notes
- Fields to prioritize vs ignore
- Potential issues to handle

**Step 3: Final commit**

```bash
git add docs/plans/2026-02-16-espn-api-analysis.md
git commit -m "docs: complete ESPN API analysis with recommendations"
```

---

## Success Criteria

- [ ] Scoreboard endpoint documented with event ID extraction
- [ ] Leaderboard endpoint documented (both current and event-specific)
- [ ] Player stats endpoint documented with FedEx Cup points location
- [ ] Player name variations catalogued
- [ ] All mappings to target schemas defined
- [ ] Recommendations for parser implementation provided
