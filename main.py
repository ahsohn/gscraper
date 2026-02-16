"""CLI entry point for PGA Golf Scraper."""

import logging
import sys

import click

import config
from espn_client import ESPNClient
from scrapers.schedule import scrape_schedule
from scrapers.fedex_standings import scrape_fedex_standings

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


if __name__ == "__main__":
    cli()
