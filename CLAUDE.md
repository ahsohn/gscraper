# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PGA Tour golf data scraper that pulls data from ESPN's undocumented public API and outputs JSON files. These JSON files are consumed by Google Apps Script to populate Google Sheets, which serve as the data source for other applications (e.g., fantasy golf league manager).

## Current Implementation Status

### Implemented (MVP Complete)
- `config.py` - API URLs, file paths, rate limiting settings, season year
- `espn_client.py` - API wrapper with retry logic, rate limiting, error handling
- `output_manager.py` - JSON file writing with timestamps
- `scrapers/schedule.py` - Fetch season schedule (48 events)
- `scrapers/fedex_standings.py` - Fetch FedEx Cup standings (top 50 players)
- `scrapers/tournament_results.py` - Aggregate results from player stats API
- `main.py` - CLI entry point with Click

### Not Yet Implemented
- `scrapers/leaderboard.py` - Active tournament leaderboard
- `name_normalizer.py` - Player name normalization (not needed for MVP - ESPN provides clean names)
- `player_registry.json` - Player alias mapping (deferred)
- Cron job setup
- Google Apps Script consumer

## Architecture

```
Python Scraper (cron on local machine)
    ├── Fetches from ESPN API endpoints
    └── Outputs JSON files:
        ├── tournament_schedule.json      ✓ Implemented
        ├── fedex_standings.json          ✓ Implemented
        ├── tournament_results/{id}_{slug}.json  ✓ Implemented
        └── current_leaderboard.json      ✗ Not yet implemented

Google Apps Script (destination Google Sheet)
    ├── Reads JSON files (via GitHub raw URLs)
    └── Populates tabs: Schedule, Leaderboard, FedEx Standings, Results
```

## ESPN API Endpoints (Undocumented)

- **Schedule/Scoreboard:** `https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard`
- **Statistics (FedEx):** `https://site.api.espn.com/apis/site/v2/sports/golf/pga/statistics`
- **Player Stats:** `https://site.web.api.espn.com/apis/common/v3/sports/golf/athletes/{athleteId}/stats?season=2026`
- **Leaderboard:** `https://site.api.espn.com/apis/site/v2/sports/golf/pga/leaderboard` (add `?event={eventId}` for specific events)

These are unofficial endpoints - build in error handling and rate limiting (1.5 second delays between requests).

## CLI Commands

```bash
python main.py schedule                    # Fetch/update season schedule (48 events)
python main.py fedex                       # Fetch FedEx Cup standings (top 50)
python main.py results --max-players N     # Aggregate tournament results
python main.py all --max-players N         # Run all scrapers
python main.py --help                      # Show all commands
```

## Output JSON Structure

### tournament_schedule.json
```json
{
  "season": 2026,
  "last_updated": "2026-02-16T...",
  "events": [
    {"event_id": "401811927", "name": "The Sentry", "start_date": "2026-01-08", "end_date": "2026-01-11"}
  ]
}
```

### fedex_standings.json
```json
{
  "season": 2026,
  "last_updated": "2026-02-16T...",
  "standings": [
    {"rank": 1, "athlete_id": "4690755", "name": "Chris Gotterup", "fedex_points": 1066}
  ]
}
```

### tournament_results/{event_id}_{slug}.json
```json
{
  "event_id": "401811928",
  "name": "Sony Open in Hawaii",
  "last_updated": "2026-02-16T...",
  "results": [
    {"athlete_id": "4690755", "name": "Chris Gotterup", "position": "1", "fedex_points": 500}
  ]
}
```

## Technical Stack

- Python 3.10+
- Dependencies: `requests`, `click` (see requirements.txt)
- Logging via Python `logging` module

## Next Steps

1. Add `scrapers/leaderboard.py` for active tournament data
2. Set up cron job for automated scraping
3. Create Google Apps Script to consume JSON files
4. (Optional) Add player name normalization if needed for external data sources
