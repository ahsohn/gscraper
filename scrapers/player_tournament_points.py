"""Fetch FedEx points for specific players from the most recent tournament."""

import csv
import logging
from typing import Any

from espn_client import ESPNClient

logger = logging.getLogger(__name__)


def _normalize_name(name: str) -> str:
    """Normalize a name for comparison (lowercase, strip whitespace)."""
    return name.lower().strip()


def _find_athlete_in_field(name: str, field: list[dict]) -> tuple[str | None, str | None]:
    """Find athlete ID by name from the tournament field.

    Args:
        name: Player name to search for
        field: List of player dictionaries with 'name' and 'athlete_id'

    Returns:
        Tuple of (athlete_id, matched_name) if found, (None, None) otherwise
    """
    normalized_input = _normalize_name(name)

    # Exact match first
    for player in field:
        if _normalize_name(player["name"]) == normalized_input:
            return player["athlete_id"], player["name"]

    # Try partial match (last name + first initial)
    input_parts = normalized_input.split()
    if input_parts:
        input_last = input_parts[-1]
        for player in field:
            player_parts = _normalize_name(player["name"]).split()
            if player_parts and player_parts[-1] == input_last:
                # Check if first name initial matches too
                if len(input_parts) > 1 and len(player_parts) > 1:
                    if player_parts[0].startswith(input_parts[0][0]):
                        return player["athlete_id"], player["name"]

    return None, None


def _get_tournament_result(player_stats: dict, event_id: str) -> dict | None:
    """Extract a specific tournament result from player stats.

    Args:
        player_stats: Raw API response from player stats endpoint
        event_id: The event ID to look for

    Returns:
        Dictionary with event info and FedEx points, or None if not found
    """
    leagues_stats = player_stats.get("leaguesStats", [])
    if not leagues_stats:
        return None

    events_stats = leagues_stats[0].get("eventsStats", [])
    if not events_stats:
        return None

    for event_stat in events_stats:
        stat_event_id = str(event_stat.get("id", ""))

        if stat_event_id != event_id:
            continue

        event_name = event_stat.get("name", "")

        # Get competition data
        competitions = event_stat.get("competitions", [])
        if not competitions:
            return None

        competition = competitions[0]
        competitors = competition.get("competitors", [])
        if not competitors:
            return None

        competitor = competitors[0]

        # Extract position
        position = ""
        status = competitor.get("status", {})
        position_data = status.get("position", {})
        position = position_data.get("displayName", "")

        # Extract FedEx points
        fedex_points = 0
        stats = competitor.get("stats", [])
        for stat in stats:
            if isinstance(stat, dict) and stat.get("name") == "cupPoints":
                try:
                    fedex_points = int(float(stat.get("value", 0)))
                except (ValueError, TypeError):
                    fedex_points = 0
                break

        return {
            "event_id": stat_event_id,
            "event_name": event_name,
            "position": position,
            "fedex_points": fedex_points,
        }

    return None


def read_player_names_from_csv(csv_path: str) -> list[str]:
    """Read player names from first column of a CSV file.

    Args:
        csv_path: Path to CSV file

    Returns:
        List of player names
    """
    names = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].strip():
                # Skip header if it looks like one
                if row[0].lower() in ("name", "player", "player name", "golfer"):
                    continue
                names.append(row[0].strip())
    return names


def get_player_points(
    player_names: list[str],
    client: ESPNClient | None = None,
) -> list[dict[str, Any]]:
    """Get FedEx points for a list of players from the current tournament.

    Looks up players from the current tournament field and returns their
    FedEx points for that specific tournament.

    Args:
        player_names: List of golfer names to look up
        client: Optional ESPNClient instance

    Returns:
        List of dictionaries with player name, tournament, position, and points
    """
    if client is None:
        client = ESPNClient()

    logger.info(f"Looking up points for {len(player_names)} players...")

    # Get current tournament info and field
    scoreboard = client.get_scoreboard()
    events = scoreboard.get("events", [])
    if not events:
        logger.error("No current tournament found")
        return [{"input_name": name, "found": False, "error": "No current tournament"}
                for name in player_names]

    current_event = events[0]
    current_event_id = str(current_event.get("id", ""))
    current_event_name = current_event.get("name", "")
    logger.info(f"Current tournament: {current_event_name} (ID: {current_event_id})")

    # Build field from competitors
    field = []
    competitions = current_event.get("competitions", [])
    if competitions:
        competitors = competitions[0].get("competitors", [])
        for competitor in competitors:
            athlete = competitor.get("athlete", {})
            field.append({
                "athlete_id": str(competitor.get("id", "")),
                "name": athlete.get("displayName", ""),
            })

    logger.info(f"Tournament field has {len(field)} players")

    results = []

    for name in player_names:
        athlete_id, matched_name = _find_athlete_in_field(name, field)

        if not athlete_id:
            logger.warning(f"Could not find player in tournament field: {name}")
            results.append({
                "input_name": name,
                "found": False,
                "error": "Player not found in current tournament field",
            })
            continue

        if not matched_name:
            matched_name = name

        try:
            player_stats = client.get_player_stats(athlete_id)
            tournament_result = _get_tournament_result(player_stats, current_event_id)

            if tournament_result:
                results.append({
                    "input_name": name,
                    "matched_name": matched_name,
                    "athlete_id": athlete_id,
                    "found": True,
                    "tournament": tournament_result["event_name"],
                    "position": tournament_result["position"],
                    "fedex_points": tournament_result["fedex_points"],
                })
            else:
                results.append({
                    "input_name": name,
                    "matched_name": matched_name,
                    "athlete_id": athlete_id,
                    "found": True,
                    "fedex_points": 0,
                    "error": f"No results for {current_event_name}",
                })

        except Exception as e:
            logger.warning(f"Failed to fetch stats for {name}: {e}")
            results.append({
                "input_name": name,
                "matched_name": matched_name,
                "athlete_id": athlete_id,
                "found": True,
                "error": str(e),
            })

    return results


def write_results_to_csv(results: list[dict], output_path: str) -> None:
    """Write player points results to a CSV file.

    Args:
        results: List of result dictionaries from get_player_points
        output_path: Path to output CSV file
    """
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Player", "FedEx Points"])

        for result in results:
            name = result.get("matched_name") or result.get("input_name")
            if result.get("found") and "fedex_points" in result:
                points = result["fedex_points"]
            else:
                points = ""  # Leave blank if not found or error
            writer.writerow([name, points])

    logger.info(f"Wrote results to {output_path}")
