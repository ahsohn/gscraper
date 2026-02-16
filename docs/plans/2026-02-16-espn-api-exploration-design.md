# ESPN API Exploration Design

## Goal

Explore ESPN's undocumented PGA golf API endpoints to understand actual response structures before building parsers for the golf data scraper.

## Approach

Browser-based fetching of three endpoints with real-time analysis. This allows direct inspection of live API responses and immediate identification of any differences between spec assumptions and actual API behavior.

## Endpoints to Explore

### 1. Scoreboard (Schedule)
- **URL:** `https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard`
- **Purpose:** Get full season schedule with event IDs, tournament names, dates, courses, purse info
- **Secondary purpose:** Extract event IDs and athlete IDs for subsequent endpoint calls

### 2. Leaderboard
- **URL:** `https://site.api.espn.com/apis/site/v2/sports/golf/pga/leaderboard`
- **URL (specific event):** `https://site.api.espn.com/apis/site/v2/sports/golf/pga/leaderboard?event={eventId}`
- **Purpose:** Get tournament leaderboard with player names, ESPN athlete IDs, scores, positions, status
- **Tests:** Fetch both current tournament and a specific historical event

### 3. Player Stats
- **URL:** `https://site.web.api.espn.com/apis/common/v3/sports/golf/athletes/{athleteId}/stats?season=2026`
- **Purpose:** Get individual player stats including FedEx Cup points, earnings, events played
- **Dependency:** Requires athlete ID discovered from leaderboard response

## Deliverable

A markdown document (`docs/plans/2026-02-16-espn-api-analysis.md`) containing:

### Structure
1. **Executive Summary** — Key findings and surprises vs. spec assumptions
2. **Scoreboard Endpoint** — Request/response details, JSON structure, mapping to tournament_schedule.json
3. **Leaderboard Endpoint** — Request/response details, JSON structure, mapping to current_leaderboard.json
4. **Player Stats Endpoint** — Request/response details, JSON structure, mapping to fedex_standings.json
5. **Player Name Observations** — Examples of name variations found in the data
6. **Recommendations** — Any spec adjustments needed based on actual API behavior

### What to Document for Each Endpoint
- Full response structure (nested objects, arrays)
- Data types and formats (dates, scores, IDs)
- Which fields map to target JSON schemas from golf-scraper-prompt.md
- Missing or unexpected fields
- Rate limiting headers or caching indicators

## Success Criteria

- All three endpoints successfully fetched
- JSON structures fully documented
- Mappings to target schemas clearly defined
- Any gaps between spec and reality identified
- Recommendations for parser implementation provided
