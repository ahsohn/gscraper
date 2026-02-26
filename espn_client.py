"""ESPN API client with rate limiting and retry logic."""

import logging
import time
from typing import Any

import requests

import config

logger = logging.getLogger(__name__)


class ESPNClient:
    """Client for fetching data from ESPN's undocumented golf API."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self._last_request_time = 0

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < config.REQUEST_DELAY_SECONDS:
            sleep_time = config.REQUEST_DELAY_SECONDS - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _request(self, url: str, params: dict | None = None) -> dict[str, Any]:
        """Make a request with retry logic and rate limiting."""
        self._rate_limit()

        for attempt in range(config.MAX_RETRIES):
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                wait_time = config.RETRY_BACKOFF_FACTOR ** attempt
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{config.MAX_RETRIES}): {e}"
                )
                if attempt < config.MAX_RETRIES - 1:
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All retries failed for {url}")
                    raise

    def get_scoreboard(self) -> dict[str, Any]:
        """Fetch the scoreboard/schedule data."""
        logger.info("Fetching scoreboard data...")
        return self._request(config.SCOREBOARD_URL)

    def get_statistics(self) -> dict[str, Any]:
        """Fetch FedEx standings and player statistics."""
        logger.info("Fetching statistics data...")
        return self._request(config.STATISTICS_URL)

    def get_player_stats(self, athlete_id: str) -> dict[str, Any]:
        """Fetch individual player stats for the current season."""
        url = config.PLAYER_STATS_URL.format(athlete_id=athlete_id)
        params = {"season": config.CURRENT_SEASON}
        logger.debug(f"Fetching stats for athlete {athlete_id}...")
        return self._request(url, params=params)

    def search_player(self, query: str) -> dict[str, Any] | None:
        """Search for a player by name.

        Args:
            query: Player name to search for

        Returns:
            Search result dict or None if not found
        """
        import urllib.parse
        url = f"{config.SEARCH_URL}?query={urllib.parse.quote(query)}&limit=5"
        logger.debug(f"Searching for player: {query}")
        try:
            return self._request(url)
        except Exception as e:
            logger.warning(f"Search failed for '{query}': {e}")
            return None

    def get_current_tournament_field(self) -> list[dict[str, Any]]:
        """Fetch the field (competitors) from the current/most recent tournament.

        Returns:
            List of player dictionaries with athlete_id, name, and score
        """
        logger.info("Fetching current tournament field...")
        data = self.get_scoreboard()

        players = []
        events = data.get("events", [])

        if not events:
            logger.warning("No active events found in scoreboard")
            return players

        event = events[0]
        competitions = event.get("competitions", [])

        if not competitions:
            return players

        competitors = competitions[0].get("competitors", [])

        for competitor in competitors:
            athlete = competitor.get("athlete", {})
            players.append({
                "athlete_id": str(competitor.get("id", "")),
                "name": athlete.get("displayName", ""),
                "score": competitor.get("score", ""),
            })

        logger.info(f"Found {len(players)} players in current tournament")
        return players
