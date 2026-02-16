"""Configuration constants for the PGA Golf Scraper."""

from pathlib import Path

# ESPN API URLs
SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard"
STATISTICS_URL = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/statistics"
PLAYER_STATS_URL = "https://site.web.api.espn.com/apis/common/v3/sports/golf/athletes/{athlete_id}/stats"

# Season configuration
CURRENT_SEASON = 2026

# Rate limiting
REQUEST_DELAY_SECONDS = 1.5
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2

# Output paths
OUTPUT_DIR = Path(__file__).parent / "output"
TOURNAMENT_RESULTS_DIR = OUTPUT_DIR / "tournament_results"

# Scraper limits
MAX_PLAYERS_TO_FETCH = 150
