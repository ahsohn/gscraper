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
