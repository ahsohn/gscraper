# ESPN Player ID Mapping Design

## Overview

Add ESPN player IDs to the GolfLeagueManager `golfers` table and fix player names with incorrect characters (e.g., Cyrillic lookalikes in "Sepp Straka" and "Hideki Matsuyama"). This enables easier score scraping by matching on ESPN IDs instead of fuzzy name matching.

## Scope

- **Database:** Add `espn_id` column to `golfers` table
- **gscraper:** Add two new CLI commands for matching and SQL generation
- **Data:** ~200 golfers in database, ~50 available in ESPN top standings

## Approach

CSV-based workflow with human review before any database changes:

1. Export golfers from Neon to CSV
2. Run fuzzy matcher against ESPN data
3. Review/edit the mapping CSV
4. Generate SQL update statements
5. Apply migration and updates to database

## Database Schema Change

New migration in GolfLeagueManager: `drizzle/migrations/0003_add_espn_id.sql`

```sql
ALTER TABLE golfers ADD COLUMN espn_id TEXT;
```

- `TEXT` type matches ESPN ID format (e.g., "5860")
- Nullable since not all golfers will have ESPN IDs
- No unique constraint needed

## New gscraper Commands

### `match-golfers`

```bash
python main.py match-golfers golfers.csv --output golfer_mapping.csv
```

**Input:** CSV with columns `golfer_id`, `name`

**Process:**
1. Load ESPN players from `output/fedex_standings.json`
2. Fuzzy match each golfer using `rapidfuzz` library
3. Assign confidence scores and status

**Output:** `golfer_mapping.csv`

| Column | Description |
|--------|-------------|
| golfer_id | Internal database ID |
| current_name | Name currently in database |
| espn_name | Matched ESPN name (if found) |
| espn_id | ESPN athlete_id (if found) |
| confidence | Match score 0-100 |
| status | MATCH (>=95), REVIEW (70-94), NO_MATCH (<70) |

### `generate-sql`

```bash
python main.py generate-sql golfer_mapping.csv --output update_golfers.sql
```

**Input:** Reviewed mapping CSV

**Output:** SQL file with UPDATE statements:

```sql
-- Name fix + ESPN ID
UPDATE golfers SET name = 'Hideki Matsuyama', espn_id = '5860' WHERE golfer_id = 42;

-- ESPN ID only (name already correct)
UPDATE golfers SET espn_id = '9478' WHERE golfer_id = 17;
```

## Fuzzy Matching Strategy

**Library:** `rapidfuzz` (add to requirements.txt)

**Algorithm:** `token_sort_ratio` scorer
- Handles word order differences ("Si Woo Kim" vs "Kim Si Woo")
- Good for names where first/last might be swapped

**Normalization:**
- Lowercase
- Strip whitespace
- Replace Cyrillic lookalikes with ASCII equivalents

**Confidence thresholds:**
- >= 95: `MATCH` - high confidence, likely correct
- 70-94: `REVIEW` - needs human verification
- < 70: `NO_MATCH` - no good candidate found

## File Structure

New files in gscraper:

```
gscraper/
├── scrapers/
│   └── player_matcher.py    # Matching logic
├── main.py                  # Add commands
├── requirements.txt         # Add rapidfuzz
└── output/
    └── (generated mapping files)
```

## Workflow

```
1. Export golfers from Neon
   SELECT golfer_id, name FROM golfers;
   → Save as golfers.csv

2. Run matcher
   python main.py match-golfers golfers.csv
   → Outputs output/golfer_mapping.csv

3. Review & edit golfer_mapping.csv
   - Verify REVIEW matches
   - Manually add ESPN IDs for NO_MATCH rows
   - Fix any incorrect matches

4. Generate SQL
   python main.py generate-sql golfer_mapping.csv
   → Outputs output/update_golfers.sql

5. Apply in GolfLeagueManager
   - Run 0003_add_espn_id.sql migration
   - Run update_golfers.sql in Neon console
```

## Out of Scope

- Automatic database connection from gscraper (requires manual SQL execution)
- Fetching more than top-50 ESPN players (manual lookup for others)
- Ongoing sync (this is a one-time migration tool)
