"""Player matching utilities for ESPN ID mapping."""

import csv
from pathlib import Path

from rapidfuzz import fuzz, process

# Cyrillic to ASCII character mappings
CYRILLIC_TO_ASCII = {
    '\u0435': 'e',  # Cyrillic е -> e
    '\u0430': 'a',  # Cyrillic а -> a
    '\u043e': 'o',  # Cyrillic о -> o
    '\u0440': 'p',  # Cyrillic р -> p (looks like p)
    '\u0441': 'c',  # Cyrillic с -> c
    '\u0443': 'y',  # Cyrillic у -> y
    '\u0445': 'x',  # Cyrillic х -> x
}


def normalize_name(name: str) -> str:
    """Normalize a name for comparison.

    Args:
        name: Player name to normalize

    Returns:
        Lowercase name with Cyrillic chars replaced and whitespace stripped
    """
    # Lowercase
    result = name.lower()

    # Replace Cyrillic lookalikes with ASCII
    for cyrillic, ascii_char in CYRILLIC_TO_ASCII.items():
        result = result.replace(cyrillic, ascii_char)

    # Strip whitespace
    return result.strip()


def find_best_match(
    golfer_name: str,
    espn_players: list[dict],
    threshold: int = 70
) -> tuple[str | None, str | None, int]:
    """Find the best matching ESPN player for a golfer name.

    Args:
        golfer_name: Name to match
        espn_players: List of ESPN player dicts with 'name' and 'athlete_id'
        threshold: Minimum score to consider a match (0-100)

    Returns:
        Tuple of (espn_name, espn_id, confidence_score)
        Returns (None, None, score) if no match above threshold
    """
    if not espn_players:
        return (None, None, 0)

    normalized_input = normalize_name(golfer_name)

    # Build lookup dict: normalized_name -> player
    player_lookup = {}
    choices = []
    for player in espn_players:
        norm = normalize_name(player["name"])
        player_lookup[norm] = player
        choices.append(norm)

    # Use token_sort_ratio for word order flexibility
    result = process.extractOne(
        normalized_input,
        choices,
        scorer=fuzz.token_sort_ratio
    )

    if result is None:
        return (None, None, 0)

    matched_norm, score, _ = result

    if score < threshold:
        return (None, None, score)

    player = player_lookup[matched_norm]
    return (player["name"], player["athlete_id"], score)


def get_status(confidence: int) -> str:
    """Determine match status from confidence score."""
    if confidence >= 95:
        return "MATCH"
    elif confidence >= 70:
        return "REVIEW"
    else:
        return "NO_MATCH"


def match_golfers(
    golfers: list[dict],
    espn_players: list[dict]
) -> list[dict]:
    """Match a list of golfers against ESPN players.

    Args:
        golfers: List of dicts with 'golfer_id' and 'name'
        espn_players: List of ESPN player dicts

    Returns:
        List of match result dicts
    """
    results = []

    for golfer in golfers:
        espn_name, espn_id, confidence = find_best_match(
            golfer["name"],
            espn_players
        )

        results.append({
            "golfer_id": golfer["golfer_id"],
            "current_name": golfer["name"],
            "espn_name": espn_name or "",
            "espn_id": espn_id or "",
            "confidence": confidence,
            "status": get_status(confidence),
        })

    return results


def read_golfers_csv(filepath: str) -> list[dict]:
    """Read golfers from a CSV file.

    Expected columns: golfer_id, name (additional columns ignored)

    Args:
        filepath: Path to CSV file

    Returns:
        List of golfer dicts with golfer_id (int) and name (str)
    """
    golfers = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            golfers.append({
                "golfer_id": int(row["golfer_id"]),
                "name": row["name"],
            })
    return golfers


def write_mapping_csv(results: list[dict], filepath: str) -> None:
    """Write matching results to a CSV file.

    Args:
        results: List of match result dicts
        filepath: Output path
    """
    fieldnames = ["golfer_id", "current_name", "espn_name", "espn_id", "confidence", "status"]

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
