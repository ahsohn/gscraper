# ESPN Player ID Mapping Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add ESPN player ID matching to gscraper and database migration to GolfLeagueManager, enabling score scraping by ID instead of name.

**Architecture:** Two new CLI commands in gscraper (`match-golfers`, `generate-sql`) that use fuzzy matching to map golfer names to ESPN athlete IDs. A CSV workflow allows human review before generating SQL updates for the GolfLeagueManager database.

**Tech Stack:** Python, rapidfuzz (fuzzy matching), Click CLI, CSV I/O

---

## Task 1: Add Dependencies

**Files:**
- Modify: `requirements.txt`

**Step 1: Add rapidfuzz and pytest**

```
requests>=2.31.0
click>=8.1.0
rapidfuzz>=3.6.0
pytest>=8.0.0
```

**Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: Successfully installed rapidfuzz and pytest

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add rapidfuzz and pytest dependencies"
```

---

## Task 2: Create Player Matcher Module - Normalization

**Files:**
- Create: `scrapers/player_matcher.py`
- Create: `tests/test_player_matcher.py`

**Step 1: Create tests directory and test file**

Create `tests/__init__.py` (empty file)

Create `tests/test_player_matcher.py`:

```python
"""Tests for player_matcher module."""

import pytest
from scrapers.player_matcher import normalize_name


class TestNormalizeName:
    """Tests for name normalization."""

    def test_lowercase(self):
        assert normalize_name("Scottie Scheffler") == "scottie scheffler"

    def test_strip_whitespace(self):
        assert normalize_name("  Scottie Scheffler  ") == "scottie scheffler"

    def test_cyrillic_e_replaced(self):
        # Cyrillic 'е' (U+0435) should become ASCII 'e'
        assert normalize_name("Hidеki Matsuyama") == "hideki matsuyama"

    def test_cyrillic_a_replaced(self):
        # Cyrillic 'а' (U+0430) should become ASCII 'a'
        assert normalize_name("Sеpp Strаka") == "sepp straka"

    def test_multiple_cyrillic_chars(self):
        # Multiple replacements
        assert normalize_name("Tеst Nаmе") == "test name"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_player_matcher.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'scrapers.player_matcher'"

**Step 3: Create minimal player_matcher.py**

Create `scrapers/player_matcher.py`:

```python
"""Player matching utilities for ESPN ID mapping."""

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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_player_matcher.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add tests/ scrapers/player_matcher.py
git commit -m "feat: add name normalization with Cyrillic replacement"
```

---

## Task 3: Add Fuzzy Matching Function

**Files:**
- Modify: `scrapers/player_matcher.py`
- Modify: `tests/test_player_matcher.py`

**Step 1: Add tests for fuzzy matching**

Add to `tests/test_player_matcher.py`:

```python
from scrapers.player_matcher import normalize_name, find_best_match


class TestFindBestMatch:
    """Tests for fuzzy matching."""

    @pytest.fixture
    def espn_players(self):
        """Sample ESPN player data."""
        return [
            {"athlete_id": "9478", "name": "Scottie Scheffler"},
            {"athlete_id": "5860", "name": "Hideki Matsuyama"},
            {"athlete_id": "8961", "name": "Sepp Straka"},
            {"athlete_id": "7081", "name": "Si Woo Kim"},
        ]

    def test_exact_match(self, espn_players):
        name, espn_id, confidence = find_best_match("Scottie Scheffler", espn_players)
        assert name == "Scottie Scheffler"
        assert espn_id == "9478"
        assert confidence == 100

    def test_cyrillic_match(self, espn_players):
        # Cyrillic 'е' in Hidеki
        name, espn_id, confidence = find_best_match("Hidеki Matsuyama", espn_players)
        assert name == "Hideki Matsuyama"
        assert espn_id == "5860"
        assert confidence >= 95

    def test_case_insensitive(self, espn_players):
        name, espn_id, confidence = find_best_match("scottie scheffler", espn_players)
        assert espn_id == "9478"
        assert confidence == 100

    def test_no_match(self, espn_players):
        name, espn_id, confidence = find_best_match("Unknown Player", espn_players)
        assert name is None
        assert espn_id is None
        assert confidence < 70

    def test_partial_match(self, espn_players):
        # Should still find Si Woo Kim
        name, espn_id, confidence = find_best_match("Kim Si Woo", espn_players)
        assert espn_id == "7081"
        assert confidence >= 70
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_player_matcher.py::TestFindBestMatch -v`
Expected: FAIL with "ImportError: cannot import name 'find_best_match'"

**Step 3: Implement find_best_match**

Add to `scrapers/player_matcher.py`:

```python
from rapidfuzz import fuzz, process


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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_player_matcher.py -v`
Expected: All 10 tests PASS

**Step 5: Commit**

```bash
git add scrapers/player_matcher.py tests/test_player_matcher.py
git commit -m "feat: add fuzzy matching with rapidfuzz"
```

---

## Task 4: Add Batch Matching Function

**Files:**
- Modify: `scrapers/player_matcher.py`
- Modify: `tests/test_player_matcher.py`

**Step 1: Add tests for batch matching**

Add to `tests/test_player_matcher.py`:

```python
from scrapers.player_matcher import normalize_name, find_best_match, match_golfers


class TestMatchGolfers:
    """Tests for batch matching."""

    @pytest.fixture
    def espn_players(self):
        return [
            {"athlete_id": "9478", "name": "Scottie Scheffler"},
            {"athlete_id": "5860", "name": "Hideki Matsuyama"},
            {"athlete_id": "8961", "name": "Sepp Straka"},
        ]

    @pytest.fixture
    def golfers(self):
        return [
            {"golfer_id": 1, "name": "Scottie Scheffler"},
            {"golfer_id": 2, "name": "Hidеki Matsuyama"},  # Cyrillic е
            {"golfer_id": 3, "name": "Unknown Player"},
        ]

    def test_returns_all_golfers(self, golfers, espn_players):
        results = match_golfers(golfers, espn_players)
        assert len(results) == 3

    def test_match_status(self, golfers, espn_players):
        results = match_golfers(golfers, espn_players)
        # Exact match
        assert results[0]["status"] == "MATCH"
        # Cyrillic match (high confidence)
        assert results[1]["status"] in ["MATCH", "REVIEW"]
        # No match
        assert results[2]["status"] == "NO_MATCH"

    def test_preserves_golfer_id(self, golfers, espn_players):
        results = match_golfers(golfers, espn_players)
        assert results[0]["golfer_id"] == 1
        assert results[1]["golfer_id"] == 2

    def test_includes_current_name(self, golfers, espn_players):
        results = match_golfers(golfers, espn_players)
        assert results[0]["current_name"] == "Scottie Scheffler"
        assert "Hidеki" in results[1]["current_name"]  # Preserves original
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_player_matcher.py::TestMatchGolfers -v`
Expected: FAIL with "ImportError: cannot import name 'match_golfers'"

**Step 3: Implement match_golfers**

Add to `scrapers/player_matcher.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_player_matcher.py -v`
Expected: All 14 tests PASS

**Step 5: Commit**

```bash
git add scrapers/player_matcher.py tests/test_player_matcher.py
git commit -m "feat: add batch matching function"
```

---

## Task 5: Add CSV I/O Functions

**Files:**
- Modify: `scrapers/player_matcher.py`
- Modify: `tests/test_player_matcher.py`

**Step 1: Add tests for CSV functions**

Add to `tests/test_player_matcher.py`:

```python
import csv
from pathlib import Path
from scrapers.player_matcher import read_golfers_csv, write_mapping_csv


class TestCSVIO:
    """Tests for CSV reading and writing."""

    def test_read_golfers_csv(self, tmp_path):
        csv_file = tmp_path / "golfers.csv"
        csv_file.write_text("golfer_id,name\n1,Scottie Scheffler\n2,Rory McIlroy\n")

        golfers = read_golfers_csv(str(csv_file))

        assert len(golfers) == 2
        assert golfers[0]["golfer_id"] == 1
        assert golfers[0]["name"] == "Scottie Scheffler"

    def test_read_golfers_csv_with_extra_columns(self, tmp_path):
        csv_file = tmp_path / "golfers.csv"
        csv_file.write_text("golfer_id,name,extra\n1,Scottie Scheffler,ignored\n")

        golfers = read_golfers_csv(str(csv_file))

        assert golfers[0]["golfer_id"] == 1
        assert golfers[0]["name"] == "Scottie Scheffler"

    def test_write_mapping_csv(self, tmp_path):
        output_file = tmp_path / "mapping.csv"
        results = [
            {
                "golfer_id": 1,
                "current_name": "Test Player",
                "espn_name": "Test Player",
                "espn_id": "12345",
                "confidence": 100,
                "status": "MATCH",
            }
        ]

        write_mapping_csv(results, str(output_file))

        content = output_file.read_text()
        assert "golfer_id,current_name,espn_name,espn_id,confidence,status" in content
        assert "1,Test Player,Test Player,12345,100,MATCH" in content
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_player_matcher.py::TestCSVIO -v`
Expected: FAIL with "ImportError: cannot import name 'read_golfers_csv'"

**Step 3: Implement CSV functions**

Add to `scrapers/player_matcher.py`:

```python
import csv
from pathlib import Path


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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_player_matcher.py -v`
Expected: All 17 tests PASS

**Step 5: Commit**

```bash
git add scrapers/player_matcher.py tests/test_player_matcher.py
git commit -m "feat: add CSV I/O functions for golfer matching"
```

---

## Task 6: Add SQL Generation Function

**Files:**
- Modify: `scrapers/player_matcher.py`
- Modify: `tests/test_player_matcher.py`

**Step 1: Add tests for SQL generation**

Add to `tests/test_player_matcher.py`:

```python
from scrapers.player_matcher import generate_sql_updates


class TestGenerateSQL:
    """Tests for SQL generation."""

    def test_generates_espn_id_only(self):
        results = [{
            "golfer_id": 1,
            "current_name": "Scottie Scheffler",
            "espn_name": "Scottie Scheffler",
            "espn_id": "9478",
            "confidence": 100,
            "status": "MATCH",
        }]

        sql = generate_sql_updates(results)

        assert "UPDATE golfers SET espn_id = '9478' WHERE golfer_id = 1;" in sql
        assert "SET name" not in sql  # Name unchanged

    def test_generates_name_fix_and_id(self):
        results = [{
            "golfer_id": 2,
            "current_name": "Hidеki Matsuyama",  # Cyrillic е
            "espn_name": "Hideki Matsuyama",
            "espn_id": "5860",
            "confidence": 95,
            "status": "MATCH",
        }]

        sql = generate_sql_updates(results)

        assert "SET name = 'Hideki Matsuyama', espn_id = '5860'" in sql

    def test_skips_empty_espn_id(self):
        results = [{
            "golfer_id": 3,
            "current_name": "Unknown Player",
            "espn_name": "",
            "espn_id": "",
            "confidence": 0,
            "status": "NO_MATCH",
        }]

        sql = generate_sql_updates(results)

        assert "Unknown Player" not in sql
        assert "golfer_id = 3" not in sql

    def test_escapes_single_quotes(self):
        results = [{
            "golfer_id": 4,
            "current_name": "Tom O'Brien",
            "espn_name": "Tom O'Brien",
            "espn_id": "12345",
            "confidence": 100,
            "status": "MATCH",
        }]

        sql = generate_sql_updates(results)

        assert "O''Brien" in sql  # Escaped quote
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_player_matcher.py::TestGenerateSQL -v`
Expected: FAIL with "ImportError: cannot import name 'generate_sql_updates'"

**Step 3: Implement SQL generation**

Add to `scrapers/player_matcher.py`:

```python
def generate_sql_updates(results: list[dict]) -> str:
    """Generate SQL UPDATE statements from matching results.

    Args:
        results: List of match result dicts from match_golfers

    Returns:
        SQL script as string
    """
    lines = [
        "-- Generated by gscraper match-golfers",
        "-- Review before running in Neon console",
        "",
    ]

    for r in results:
        espn_id = r.get("espn_id", "")
        if not espn_id:
            continue  # Skip unmatched

        golfer_id = r["golfer_id"]
        current_name = r["current_name"]
        espn_name = r.get("espn_name", "")

        # Escape single quotes for SQL
        espn_name_escaped = espn_name.replace("'", "''")
        espn_id_escaped = espn_id.replace("'", "''")

        # Check if name needs updating
        if current_name != espn_name and espn_name:
            # Update both name and espn_id
            lines.append(f"-- {current_name}: name fix + ESPN ID")
            lines.append(
                f"UPDATE golfers SET name = '{espn_name_escaped}', "
                f"espn_id = '{espn_id_escaped}' WHERE golfer_id = {golfer_id};"
            )
        else:
            # Update espn_id only
            lines.append(f"-- {current_name}: ESPN ID only")
            lines.append(
                f"UPDATE golfers SET espn_id = '{espn_id_escaped}' "
                f"WHERE golfer_id = {golfer_id};"
            )
        lines.append("")

    return "\n".join(lines)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_player_matcher.py -v`
Expected: All 21 tests PASS

**Step 5: Commit**

```bash
git add scrapers/player_matcher.py tests/test_player_matcher.py
git commit -m "feat: add SQL generation for golfer updates"
```

---

## Task 7: Add match-golfers CLI Command

**Files:**
- Modify: `main.py`
- Modify: `scrapers/__init__.py`

**Step 1: Update scrapers/__init__.py to export player_matcher**

Check current content and add export:

```python
"""Scrapers package."""

from .schedule import scrape_schedule
from .fedex_standings import scrape_fedex_standings, load_player_roster
from .player_matcher import (
    match_golfers,
    read_golfers_csv,
    write_mapping_csv,
    generate_sql_updates,
)
```

**Step 2: Add match-golfers command to main.py**

Add import at top of `main.py`:

```python
from scrapers.player_matcher import (
    match_golfers,
    read_golfers_csv,
    write_mapping_csv,
)
from scrapers.fedex_standings import load_player_roster
```

Add command before `if __name__ == "__main__":`:

```python
@cli.command("match-golfers")
@click.argument("input_csv", type=click.Path(exists=True))
@click.option(
    "--output",
    default="output/golfer_mapping.csv",
    help="Output CSV file path",
)
def match_golfers_cmd(input_csv: str, output: str) -> None:
    """Match golfers against ESPN player database.

    Reads golfer names from INPUT_CSV (columns: golfer_id, name) and
    fuzzy matches against ESPN FedEx standings data.

    Examples:
        python main.py match-golfers golfers.csv
        python main.py match-golfers golfers.csv --output my_mapping.csv
    """
    # Load golfers from input CSV
    golfers = read_golfers_csv(input_csv)
    click.echo(f"Loaded {len(golfers)} golfers from {input_csv}")

    # Load ESPN players
    espn_players = load_player_roster()
    click.echo(f"Loaded {len(espn_players)} ESPN players")

    # Match
    results = match_golfers(golfers, espn_players)

    # Write output
    write_mapping_csv(results, output)
    click.echo(f"Wrote mapping to {output}")

    # Summary
    matches = sum(1 for r in results if r["status"] == "MATCH")
    reviews = sum(1 for r in results if r["status"] == "REVIEW")
    no_match = sum(1 for r in results if r["status"] == "NO_MATCH")
    click.echo(f"\nSummary: {matches} MATCH, {reviews} REVIEW, {no_match} NO_MATCH")
```

**Step 3: Test the command manually**

Create a test CSV file `test_golfers.csv`:

```csv
golfer_id,name
1,Scottie Scheffler
2,Hideki Matsuyama
3,Unknown Player
```

Run: `python main.py match-golfers test_golfers.csv --output test_output.csv`
Expected: Shows summary with matches found

**Step 4: Verify output file**

Run: `cat test_output.csv`
Expected: CSV with golfer_id, current_name, espn_name, espn_id, confidence, status columns

**Step 5: Clean up and commit**

```bash
rm test_golfers.csv test_output.csv
git add main.py scrapers/__init__.py
git commit -m "feat: add match-golfers CLI command"
```

---

## Task 8: Add generate-sql CLI Command

**Files:**
- Modify: `main.py`

**Step 1: Add import for generate_sql_updates**

Update imports in `main.py`:

```python
from scrapers.player_matcher import (
    match_golfers,
    read_golfers_csv,
    write_mapping_csv,
    generate_sql_updates,
)
```

**Step 2: Add generate-sql command**

Add before `if __name__ == "__main__":`:

```python
@cli.command("generate-sql")
@click.argument("mapping_csv", type=click.Path(exists=True))
@click.option(
    "--output",
    default="output/update_golfers.sql",
    help="Output SQL file path",
)
def generate_sql_cmd(mapping_csv: str, output: str) -> None:
    """Generate SQL UPDATE statements from a mapping CSV.

    Reads the reviewed mapping CSV and generates SQL statements
    to update the golfers table with ESPN IDs and name fixes.

    Examples:
        python main.py generate-sql golfer_mapping.csv
        python main.py generate-sql mapping.csv --output updates.sql
    """
    import csv

    # Read mapping CSV
    results = []
    with open(mapping_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append({
                "golfer_id": int(row["golfer_id"]),
                "current_name": row["current_name"],
                "espn_name": row["espn_name"],
                "espn_id": row["espn_id"],
                "confidence": int(row["confidence"]),
                "status": row["status"],
            })

    click.echo(f"Read {len(results)} rows from {mapping_csv}")

    # Generate SQL
    sql = generate_sql_updates(results)

    # Write output
    with open(output, "w", encoding="utf-8") as f:
        f.write(sql)

    # Count updates
    update_count = sql.count("UPDATE golfers")
    click.echo(f"Generated {update_count} UPDATE statements")
    click.echo(f"Wrote SQL to {output}")
```

**Step 3: Test the command**

Create test mapping CSV `test_mapping.csv`:

```csv
golfer_id,current_name,espn_name,espn_id,confidence,status
1,Scottie Scheffler,Scottie Scheffler,9478,100,MATCH
2,Hidеki Matsuyama,Hideki Matsuyama,5860,95,MATCH
3,Unknown Player,,,0,NO_MATCH
```

Run: `python main.py generate-sql test_mapping.csv --output test_updates.sql`
Expected: Shows count of UPDATE statements generated

**Step 4: Verify SQL output**

Run: `cat test_updates.sql`
Expected: SQL with UPDATE statements for rows with espn_id

**Step 5: Clean up and commit**

```bash
rm test_mapping.csv test_updates.sql
git add main.py
git commit -m "feat: add generate-sql CLI command"
```

---

## Task 9: Create Database Migration

**Files:**
- Create: `../GolfLeagueManager/drizzle/migrations/0003_add_espn_id.sql`

**Step 1: Create migration file**

Create `drizzle/migrations/0003_add_espn_id.sql` in GolfLeagueManager:

```sql
-- Add ESPN athlete ID to golfers table
-- This enables matching golfers to ESPN data by ID instead of name

ALTER TABLE golfers ADD COLUMN espn_id TEXT;

-- Index for lookups by ESPN ID
CREATE INDEX idx_golfers_espn_id ON golfers(espn_id);
```

**Step 2: Commit in GolfLeagueManager**

```bash
cd ../GolfLeagueManager
git add drizzle/migrations/0003_add_espn_id.sql
git commit -m "feat: add espn_id column to golfers table"
```

---

## Task 10: Update Documentation

**Files:**
- Modify: `CLAUDE.md` (in gscraper)

**Step 1: Add player matching section to CLAUDE.md**

Add to gscraper's CLAUDE.md:

```markdown
## Player ID Matching

Match golfers from external databases to ESPN athlete IDs:

```bash
# 1. Export golfers from your database to CSV (golfer_id, name columns)

# 2. Run fuzzy matcher
python main.py match-golfers golfers.csv --output output/golfer_mapping.csv

# 3. Review and edit output/golfer_mapping.csv
#    - Verify REVIEW matches
#    - Manually add ESPN IDs for NO_MATCH rows

# 4. Generate SQL updates
python main.py generate-sql output/golfer_mapping.csv --output output/update_golfers.sql

# 5. Run the SQL in your database
```

Status values:
- `MATCH` (>=95 confidence) - High confidence, likely correct
- `REVIEW` (70-94) - Needs human verification
- `NO_MATCH` (<70) - No good candidate found
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add player ID matching instructions"
```

---

## Final Verification

**Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests pass

**Step 2: Test full workflow**

1. Create sample golfers CSV
2. Run `python main.py match-golfers`
3. Review output CSV
4. Run `python main.py generate-sql`
5. Verify SQL output

**Step 3: Clean up any test files**

```bash
rm -f test_*.csv test_*.sql
```
