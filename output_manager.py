"""Output manager for writing JSON files."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config

logger = logging.getLogger(__name__)


def ensure_output_dirs() -> None:
    """Create output directories if they don't exist."""
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    config.TOURNAMENT_RESULTS_DIR.mkdir(exist_ok=True)
    logger.debug(f"Output directories ensured at {config.OUTPUT_DIR}")


def write_json(filename: str, data: dict[str, Any], subdir: Path | None = None) -> Path:
    """Write data to a JSON file with last_updated timestamp.

    Args:
        filename: Name of the JSON file to write
        data: Dictionary to write as JSON
        subdir: Optional subdirectory within OUTPUT_DIR

    Returns:
        Path to the written file
    """
    ensure_output_dirs()

    # Add last_updated timestamp
    data["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Determine output path
    if subdir:
        output_path = subdir / filename
    else:
        output_path = config.OUTPUT_DIR / filename

    # Write JSON with pretty formatting
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"Wrote {output_path}")
    return output_path
