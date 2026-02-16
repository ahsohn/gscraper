"""Tournament results scraper - aggregates results from player stats."""

import logging
import re
from collections import defaultdict
from typing import Any

import config
from espn_client import ESPNClient
from output_manager import write_json
from scrapers.fedex_standings import load_player_roster

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    """Convert tournament name to URL-safe slug."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


def _extract_event_results(player_stats: dict, athlete_id: str, name: str) -> list[dict]:
    """Extract tournament results from a player's stats response.

    Args:
        player_stats: Raw API response from player stats endpoint
        athlete_id: Player's ESPN athlete ID
        name: Player's display name

    Returns:
        List of event result dictionaries
    """
    results = []

    # Navigate to events stats
    leagues_stats = player_stats.get("leaguesStats", [])
    if not leagues_stats:
        return results

    events_stats = leagues_stats[0].get("eventsStats", [])

    for event_stat in events_stats:
        # Event info is directly on event_stat, not in a nested "event" object
        event_id = str(event_stat.get("id", ""))
        event_name = event_stat.get("name", "")

        if not event_id:
            continue

        # Get competition data
        competitions = event_stat.get("competitions", [])
        if not competitions:
            continue

        competition = competitions[0]
        competitors = competition.get("competitors", [])
        if not competitors:
            continue

        competitor = competitors[0]

        # Extract position from status.position.displayName
        position = ""
        status = competitor.get("status", {})
        position_data = status.get("position", {})
        position = position_data.get("displayName", "")

        # Extract FedEx points from stats array - find stat with name "cupPoints"
        fedex_points = 0
        stats = competitor.get("stats", [])
        for stat in stats:
            if isinstance(stat, dict) and stat.get("name") == "cupPoints":
                try:
                    fedex_points = int(float(stat.get("value", 0)))
                except (ValueError, TypeError):
                    fedex_points = 0
                break

        results.append({
            "event_id": event_id,
            "event_name": event_name,
            "athlete_id": athlete_id,
            "name": name,
            "position": position,
            "fedex_points": fedex_points,
        })

    return results


def scrape_tournament_results(
    client: ESPNClient | None = None,
    max_players: int = config.MAX_PLAYERS_TO_FETCH,
) -> dict[str, Any]:
    """Scrape tournament results by aggregating player stats.

    Args:
        client: Optional ESPNClient instance
        max_players: Maximum number of players to fetch

    Returns:
        Dictionary mapping event_id to result data
    """
    if client is None:
        client = ESPNClient()

    logger.info(f"Scraping tournament results for up to {max_players} players...")

    # Load player roster
    roster = load_player_roster()
    roster = roster[:max_players]
    logger.info(f"Loaded {len(roster)} players from roster")

    # Aggregate results by event
    events_results: dict[str, dict] = defaultdict(lambda: {
        "event_id": "",
        "name": "",
        "results": [],
    })

    # Fetch stats for each player
    for i, player in enumerate(roster):
        athlete_id = player["athlete_id"]
        name = player["name"]

        if (i + 1) % 10 == 0:
            logger.info(f"Progress: {i + 1}/{len(roster)} players processed")

        try:
            player_stats = client.get_player_stats(athlete_id)
            event_results = _extract_event_results(player_stats, athlete_id, name)

            for result in event_results:
                event_id = result["event_id"]
                events_results[event_id]["event_id"] = event_id
                events_results[event_id]["name"] = result["event_name"]
                events_results[event_id]["results"].append({
                    "athlete_id": result["athlete_id"],
                    "name": result["name"],
                    "position": result["position"],
                    "fedex_points": result["fedex_points"],
                })

        except Exception as e:
            logger.warning(f"Failed to fetch stats for {name} ({athlete_id}): {e}")
            continue

    # Write tournament result files
    for event_id, event_data in events_results.items():
        if not event_data["results"]:
            continue

        # Sort results by position (handling non-numeric positions)
        def sort_key(r):
            pos = r["position"]
            if pos.startswith("T"):
                pos = pos[1:]
            try:
                return int(pos)
            except ValueError:
                return 9999

        event_data["results"].sort(key=sort_key)

        # Create filename
        slug = _slugify(event_data["name"])
        filename = f"{event_id}_{slug}.json"

        write_json(filename, event_data, subdir=config.TOURNAMENT_RESULTS_DIR)

    logger.info(f"Created {len(events_results)} tournament result files")
    return events_results
