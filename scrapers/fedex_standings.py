"""FedEx Cup standings scraper."""

import logging
from typing import Any

import config
from espn_client import ESPNClient
from output_manager import write_json

logger = logging.getLogger(__name__)


def scrape_fedex_standings(client: ESPNClient | None = None) -> dict[str, Any]:
    """Scrape FedEx Cup standings and player roster.

    Args:
        client: Optional ESPNClient instance (creates new one if not provided)

    Returns:
        Dictionary containing standings data with player roster
    """
    if client is None:
        client = ESPNClient()

    logger.info("Scraping FedEx Cup standings...")
    data = client.get_statistics()

    standings = []

    # Navigate to stats.categories to find FedEx Cup Points
    stats = data.get("stats", {})
    categories = stats.get("categories", [])

    # Find the FedEx Cup Points category (usually index 1, but search by name to be safe)
    fedex_leaders = []
    for cat in categories:
        if cat.get("name") == "cupPoints":
            fedex_leaders = cat.get("leaders", [])
            break

    # Process each leader
    for rank, leader in enumerate(fedex_leaders, start=1):
        athlete = leader.get("athlete", {})
        athlete_id = str(athlete.get("id", ""))
        name = athlete.get("displayName", "")

        # Get FedEx points from value
        try:
            fedex_points = int(leader.get("value", 0))
        except (ValueError, TypeError):
            fedex_points = 0

        standings.append({
            "rank": rank,
            "athlete_id": athlete_id,
            "name": name,
            "fedex_points": fedex_points,
        })

    result = {
        "season": config.CURRENT_SEASON,
        "standings": standings,
    }

    write_json("fedex_standings.json", result)
    logger.info(f"Scraped {len(standings)} players in FedEx standings")
    return result


def load_player_roster() -> list[dict[str, Any]]:
    """Load player roster from fedex_standings.json.

    Returns:
        List of player dictionaries with athlete_id and name
    """
    import json
    standings_path = config.OUTPUT_DIR / "fedex_standings.json"

    if not standings_path.exists():
        logger.warning("fedex_standings.json not found, scraping first...")
        result = scrape_fedex_standings()
        return result["standings"]

    with open(standings_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("standings", [])
