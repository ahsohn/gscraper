"""CLI entry point for PGA Golf Scraper."""

import logging
import sys

import click

import config
from espn_client import ESPNClient
from scrapers.schedule import scrape_schedule
from scrapers.fedex_standings import scrape_fedex_standings, load_player_roster
from scrapers.player_matcher import (
    match_golfers,
    read_golfers_csv,
    write_mapping_csv,
    generate_sql_updates,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(debug: bool) -> None:
    """PGA Golf Scraper - Fetch data from ESPN API."""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)


@cli.command()
def schedule() -> None:
    """Fetch and update the tournament schedule."""
    client = ESPNClient()
    result = scrape_schedule(client)
    click.echo(f"Scraped {len(result['events'])} events")


@cli.command()
def fedex() -> None:
    """Fetch FedEx Cup standings."""
    client = ESPNClient()
    result = scrape_fedex_standings(client)
    click.echo(f"Scraped {len(result['standings'])} players")


@cli.command()
@click.option(
    "--max-players",
    default=config.MAX_PLAYERS_TO_FETCH,
    help="Maximum number of players to fetch results for",
)
def results(max_players: int) -> None:
    """Aggregate tournament results from player stats."""
    from scrapers.tournament_results import scrape_tournament_results

    client = ESPNClient()
    result = scrape_tournament_results(client, max_players=max_players)
    click.echo(f"Created {len(result)} tournament result files")


@cli.command()
@click.argument("input_csv", type=click.Path(exists=True))
@click.argument("output_csv", type=click.Path())
def points(input_csv: str, output_csv: str) -> None:
    """Get FedEx points for players from the most recent tournament.

    Reads player names from INPUT_CSV (first column) and writes results to OUTPUT_CSV.

    Examples:
        python main.py points players.csv results.csv
    """
    from scrapers.player_tournament_points import (
        get_player_points,
        read_player_names_from_csv,
        write_results_to_csv,
    )

    # Read player names from CSV
    player_names = read_player_names_from_csv(input_csv)
    click.echo(f"Read {len(player_names)} player names from {input_csv}")

    if not player_names:
        click.echo("Error: No player names found in CSV.")
        return

    client = ESPNClient()
    results = get_player_points(player_names, client)

    # Write results to CSV
    write_results_to_csv(results, output_csv)
    click.echo(f"Wrote results to {output_csv}")

    # Show summary
    found = sum(1 for r in results if r.get("found"))
    not_found = len(results) - found
    click.echo(f"\nSummary: {found} found, {not_found} not found in tournament field")


@cli.command(name="all")
@click.option(
    "--max-players",
    default=config.MAX_PLAYERS_TO_FETCH,
    help="Maximum number of players to fetch results for",
)
def run_all(max_players: int) -> None:
    """Run all scrapers (schedule, fedex, results)."""
    from scrapers.tournament_results import scrape_tournament_results

    client = ESPNClient()

    click.echo("=== Scraping Schedule ===")
    schedule_result = scrape_schedule(client)
    click.echo(f"Scraped {len(schedule_result['events'])} events\n")

    click.echo("=== Scraping FedEx Standings ===")
    fedex_result = scrape_fedex_standings(client)
    click.echo(f"Scraped {len(fedex_result['standings'])} players\n")

    click.echo("=== Scraping Tournament Results ===")
    results_count = scrape_tournament_results(client, max_players=max_players)
    click.echo(f"Created {len(results_count)} tournament result files\n")

    click.echo("=== Done ===")


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
                "confidence": int(float(row["confidence"])),
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


if __name__ == "__main__":
    cli()
