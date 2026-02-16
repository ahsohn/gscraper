# Claude Code Prompt: PGA Golf Data Scraper

## Project Overview

Build a Python-based PGA Tour golf data scraper that pulls data from ESPN's undocumented public API and outputs JSON files. These JSON files will be consumed by Google Apps Script to populate Google Sheets. Other applications (like a fantasy golf league manager) will connect to the Sheets as their data source.

## Data Sources — ESPN Undocumented API

All endpoints are free, no auth required, return JSON via simple GET requests. Be respectful with request frequency.

**Key Endpoints:**

- **Season Schedule/Scoreboard:** `https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard`
  - Returns full season calendar with event IDs, tournament names, dates, courses, purse info
  
- **Tournament Leaderboard:** `https://site.api.espn.com/apis/site/v2/sports/golf/pga/leaderboard`
  - Returns current/active tournament leaderboard: player names, ESPN athlete IDs, scores (total, per-round), position, status (active/cut/withdrawn), thru hole
  - Can also query specific events by appending `?event={eventId}` (event IDs come from the scoreboard endpoint)

- **Player Stats (including FedEx Cup points):** `https://site.web.api.espn.com/apis/common/v3/sports/golf/athletes/{athleteId}/stats?season=2026`
  - Returns individual player season stats including FedEx Cup points, earnings, events played, scoring average, etc.

- **FedEx Cup Standings (alternative approach):** The ESPN stats page at `https://www.espn.com/golf/stats/player/_/table/general/sort/cupPoints/dir/desc` renders FedEx Cup rankings — investigate whether there's an underlying JSON API endpoint powering this page (check network tab pattern). If not, scrape the leaderboard data and calculate/track points from tournament results.

**Important:** These are unofficial endpoints that could change without notice. Build in error handling and don't hammer them — add reasonable delays between requests and cache responses.

## Architecture

```
Python Scraper (cron on local machine)
    ├── Fetches from ESPN API endpoints
    ├── Normalizes player names (alias system)
    ├── Outputs JSON files to a local directory
    │
    ├── tournament_schedule.json    (full season schedule)
    ├── current_leaderboard.json    (active tournament scores)
    ├── fedex_standings.json        (FedEx Cup points rankings)
    ├── player_registry.json        (canonical player name mapping)
    └── tournament_results/         (historical results per event)
         ├── 401811927_the_sentry.json
         ├── 401811928_sony_open.json
         └── ...

Google Apps Script (in the destination Google Sheet)
    ├── Reads JSON files (served via simple local HTTP server or uploaded somewhere accessible)
    ├── Populates tabs: Schedule, Leaderboard, FedEx Standings, Results
    └── Runs on a timer trigger or manual trigger
```

**Note on JSON → GAS connectivity:** Since the scraper runs locally, the JSON files need to be accessible to GAS somehow. Options to implement (pick the simplest that works):
1. **GitHub Pages / GitHub repo raw files** — scraper commits JSON to a repo, GAS fetches raw URLs
2. **Simple local HTTP server** exposed via Tailscale (since you already use it)
3. **Google Drive** — scraper uploads JSON to Drive via API, GAS reads from Drive

Start with option 1 (GitHub raw files) as the default since it's simplest and Alex already has GitHub experience. Structure the scraper to commit updated JSON to a dedicated data repo.

## Player Name Normalization System

This is critical. Golf data sources are inconsistent with player names. Build a robust name-matching system:

**Known issues to handle:**
- Accent marks: "Ludvig Åberg" vs "Ludvig Aberg", "Joaquín Niemann" vs "Joaquin Niemann"
- Initial variations: "Hideki Matsuyama" vs "H. Matsuyama", "Byeong Hun An" vs "B.H. An"
- Hyphenation: "Si Woo Kim" vs "Si-Woo Kim"  
- Suffixes: "Davis Love III" vs "Davis Love"
- Preferred names: "Xander Schauffele" vs "Alexander Schauffele"

**Implementation approach:**
1. Use ESPN's `athleteId` as the canonical unique identifier for every player
2. Maintain a `player_registry.json` that maps:
   ```json
   {
     "4686086": {
       "espn_id": "4686086",
       "canonical_name": "Ludvig Åberg",
       "display_name": "Ludvig Aberg",
       "aliases": ["Ludvig Åberg", "Ludvig Aberg", "L. Åberg", "L. Aberg"],
       "normalized": "ludvig aberg"
     }
   }
   ```
3. Build a `normalize_name(name)` function that:
   - Strips accent marks (unicode normalization → ASCII folding via `unidecode`)
   - Lowercases everything
   - Removes periods, hyphens, extra spaces
   - Strips common suffixes (Jr., III, etc.)
4. Build a `match_player(input_name, registry)` function that:
   - First tries exact match on normalized name
   - Then tries matching on aliases
   - Then tries fuzzy matching (e.g., `thefuzz` / `rapidfuzz` library) with a confidence threshold
   - Returns the canonical ESPN ID or flags as "unmatched" for manual review
5. The registry should auto-grow: when the scraper encounters a new player from ESPN, it auto-creates their registry entry from the ESPN data. Manual aliases can be added for edge cases.

## Scraper Modules to Build

### 1. `config.py`
- ESPN API base URLs
- File output paths
- Request headers (use a reasonable User-Agent)
- Rate limiting settings (delay between requests)
- Current season year

### 2. `espn_client.py`
- Wrapper around ESPN API calls with:
  - Retry logic with exponential backoff
  - Rate limiting (e.g., 1-2 second delay between requests)
  - Response caching (don't re-fetch if data hasn't changed / within a time window)
  - Error handling for when ESPN changes endpoints or returns errors
  - Logging

### 3. `scrapers/schedule.py`
- Fetch full PGA season schedule
- Parse event IDs, tournament names, dates, course info, purse
- Output: `tournament_schedule.json`

### 4. `scrapers/leaderboard.py`
- Fetch current active tournament leaderboard
- Parse: player name, ESPN ID, position, total score, round scores (R1-R4), today's score, thru hole, status (active/cut/WD)
- Cross-reference with player registry for name normalization
- Output: `current_leaderboard.json`
- Also save completed tournament results to `tournament_results/{eventId}_{slug}.json`

### 5. `scrapers/fedex_standings.py`
- Approach 1: Iterate through top players and hit the individual stats endpoint to collect FedEx Cup points
- Approach 2: Find a bulk endpoint that returns standings (investigate ESPN's network calls on their stats page)
- Parse: rank, player name, ESPN ID, FedEx Cup points, events played, wins, top 10s, earnings
- Output: `fedex_standings.json`

### 6. `name_normalizer.py`
- The player name normalization system described above
- `normalize_name()`, `match_player()`, `add_player()`, `load_registry()`, `save_registry()`
- Dependencies: `unidecode`, `rapidfuzz`

### 7. `output_manager.py`
- Handles writing JSON files to the output directory
- Optionally commits and pushes to a GitHub repo (for GAS to fetch)
- Timestamps each output file with last-updated metadata

### 8. `main.py`
- CLI entry point with subcommands:
  - `python main.py schedule` — fetch/update season schedule
  - `python main.py leaderboard` — fetch current leaderboard
  - `python main.py fedex` — fetch FedEx Cup standings
  - `python main.py all` — run all scrapers
  - `python main.py results --event {eventId}` — fetch specific tournament results
- Use `argparse` or `click` for CLI

### 9. `gas/sheets_import.gs`
- Google Apps Script file that:
  - Fetches JSON from the GitHub raw URLs (or wherever hosted)
  - Parses and writes to designated sheet tabs
  - Has a menu button for manual refresh
  - Can be set on a time-based trigger (e.g., every hour during tournaments, daily otherwise)
  - Handles the name mapping — uses the canonical display_name from the registry

## JSON Output Schemas

### tournament_schedule.json
```json
{
  "season": 2026,
  "last_updated": "2026-02-15T12:00:00Z",
  "events": [
    {
      "event_id": "401811927",
      "name": "The Sentry",
      "start_date": "2026-01-08",
      "end_date": "2026-01-11",
      "course": "Plantation Course at Kapalua",
      "location": "Maui, HI",
      "purse": 20000000,
      "status": "completed",
      "winner_espn_id": "...",
      "winner_name": "..."
    }
  ]
}
```

### current_leaderboard.json
```json
{
  "event_id": "401811932",
  "event_name": "AT&T Pebble Beach Pro-Am",
  "round": 3,
  "status": "in_progress",
  "last_updated": "2026-02-15T14:30:00Z",
  "players": [
    {
      "espn_id": "10046",
      "display_name": "Akshay Bhatia",
      "position": "1",
      "total_score": -19,
      "today_score": -5,
      "thru": "F",
      "rounds": [-7, -7, -5, null],
      "status": "active"
    }
  ]
}
```

### fedex_standings.json
```json
{
  "season": 2026,
  "last_updated": "2026-02-15T12:00:00Z",
  "standings": [
    {
      "rank": 1,
      "espn_id": "...",
      "display_name": "Chris Gotterup",
      "fedex_points": 1250,
      "events_played": 6,
      "wins": 1,
      "top_10s": 3,
      "earnings": 5200000
    }
  ]
}
```

## Technical Requirements

- **Python 3.10+**
- **Dependencies:** `requests`, `unidecode`, `rapidfuzz`, `click` (or argparse)
- **No heavy frameworks** — keep it simple and lightweight
- Keep all config in a `config.py` or `.env` file (no hardcoded paths)
- Comprehensive logging (use Python `logging` module)
- Write clean, well-documented code with docstrings
- Include a `requirements.txt`
- Include a `README.md` with setup instructions, cron job examples, and architecture overview

## Cron Job Setup

Include example crontab entries in the README:
```bash
# During tournament days (Thu-Sun): update leaderboard every 30 minutes
*/30 * * * 4-0 /path/to/venv/bin/python /path/to/main.py leaderboard

# Daily: update schedule and FedEx standings  
0 6 * * * /path/to/venv/bin/python /path/to/main.py schedule fedex

# After each tournament (Monday morning): archive final results
0 8 * * 1 /path/to/venv/bin/python /path/to/main.py all
```

## Important Notes

- The ESPN API is undocumented and unofficial. Endpoints may change. Build the scraper to fail gracefully and log issues clearly so problems are easy to diagnose.
- Start by exploring the ESPN endpoints interactively (use `curl` or a test script) to understand the actual JSON response structures before building parsers. The schemas I've described above are targets — the actual ESPN response structure will dictate the parsing logic.
- The player registry is the long-term valuable asset here — even if ESPN changes their API, the registry of normalized names carries over to any data source.
- This scraper is meant to be a data service that other apps consume via the JSON output / Google Sheets. Keep it focused on data collection and normalization, not presentation.
