"""Tournament schedule scraper."""

import logging
from typing import Any

import config
from espn_client import ESPNClient
from output_manager import write_json

logger = logging.getLogger(__name__)


def scrape_schedule(client: ESPNClient | None = None) -> dict[str, Any]:
    """Scrape the PGA Tour tournament schedule.

    Args:
        client: Optional ESPNClient instance (creates new one if not provided)

    Returns:
        Dictionary containing the schedule data
    """
    if client is None:
        client = ESPNClient()

    logger.info("Scraping tournament schedule...")
    data = client.get_scoreboard()

    events = []
    calendar = data.get("leagues", [{}])[0].get("calendar", [])

    for event in calendar:
        event_data = {
            "event_id": str(event.get("id", "")),
            "name": event.get("label", ""),
            "start_date": event.get("startDate", "")[:10] if event.get("startDate") else "",
            "end_date": event.get("endDate", "")[:10] if event.get("endDate") else "",
        }
        events.append(event_data)

    schedule = {
        "season": config.CURRENT_SEASON,
        "events": events,
    }

    write_json("tournament_schedule.json", schedule)
    logger.info(f"Scraped {len(events)} tournament events")
    return schedule
