"""Tests for player_matcher module."""

import csv
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from scrapers.player_matcher import (
    normalize_name,
    find_best_match,
    match_golfers,
    match_golfers_enhanced,
    read_golfers_csv,
    write_mapping_csv,
    generate_sql_updates,
    load_players_from_tournament_results,
    load_all_espn_players,
    lookup_golfer_espn,
)


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
            "current_name": "Tom OBrien",  # Different from espn_name to trigger name update
            "espn_name": "Tom O'Brien",
            "espn_id": "12345",
            "confidence": 100,
            "status": "MATCH",
        }]

        sql = generate_sql_updates(results)

        assert "O''Brien" in sql  # Escaped quote


class TestLoadPlayersFromTournamentResults:
    """Tests for loading players from tournament result files."""

    def test_load_from_empty_dir(self, tmp_path):
        """Returns empty list when no results exist."""
        with patch("config.TOURNAMENT_RESULTS_DIR", tmp_path):
            players = load_players_from_tournament_results()
            assert players == []

    def test_load_from_nonexistent_dir(self, tmp_path):
        """Returns empty list when directory doesn't exist."""
        nonexistent = tmp_path / "nonexistent"
        with patch("config.TOURNAMENT_RESULTS_DIR", nonexistent):
            players = load_players_from_tournament_results()
            assert players == []

    def test_load_single_tournament(self, tmp_path):
        """Loads players from a single tournament file."""
        tournament_data = {
            "results": [
                {"athlete_id": "9478", "name": "Scottie Scheffler", "fedex_points": 500},
                {"athlete_id": "5860", "name": "Hideki Matsuyama", "fedex_points": 300},
            ]
        }
        result_file = tmp_path / "tournament_001.json"
        result_file.write_text(json.dumps(tournament_data))

        with patch("config.TOURNAMENT_RESULTS_DIR", tmp_path):
            players = load_players_from_tournament_results()

        assert len(players) == 2
        athlete_ids = {p["athlete_id"] for p in players}
        assert "9478" in athlete_ids
        assert "5860" in athlete_ids

    def test_deduplicates_across_tournaments(self, tmp_path):
        """Same player in multiple tournaments only appears once."""
        t1_data = {
            "results": [
                {"athlete_id": "9478", "name": "Scottie Scheffler", "fedex_points": 500},
            ]
        }
        t2_data = {
            "results": [
                {"athlete_id": "9478", "name": "Scottie Scheffler", "fedex_points": 300},
                {"athlete_id": "5860", "name": "Hideki Matsuyama", "fedex_points": 400},
            ]
        }
        (tmp_path / "tournament_001.json").write_text(json.dumps(t1_data))
        (tmp_path / "tournament_002.json").write_text(json.dumps(t2_data))

        with patch("config.TOURNAMENT_RESULTS_DIR", tmp_path):
            players = load_players_from_tournament_results()

        assert len(players) == 2
        athlete_ids = [p["athlete_id"] for p in players]
        assert len(athlete_ids) == len(set(athlete_ids))  # No duplicates

    def test_skips_invalid_json(self, tmp_path):
        """Skips files with invalid JSON."""
        (tmp_path / "valid.json").write_text(json.dumps({
            "results": [{"athlete_id": "9478", "name": "Scottie Scheffler"}]
        }))
        (tmp_path / "invalid.json").write_text("not valid json {{{")

        with patch("config.TOURNAMENT_RESULTS_DIR", tmp_path):
            players = load_players_from_tournament_results()

        assert len(players) == 1
        assert players[0]["athlete_id"] == "9478"


class TestLoadAllEspnPlayers:
    """Tests for comprehensive player loading."""

    def test_returns_list(self):
        """Returns a list even with no data."""
        with patch("scrapers.player_matcher.load_players_from_tournament_results", return_value=[]):
            with patch("scrapers.fedex_standings.load_player_roster", return_value=[]):
                players = load_all_espn_players()
                assert isinstance(players, list)

    def test_combines_sources(self):
        """Combines players from both sources."""
        fedex_players = [
            {"athlete_id": "9478", "name": "Scottie Scheffler", "fedex_points": 1000},
        ]
        tournament_players = [
            {"athlete_id": "5860", "name": "Hideki Matsuyama"},
        ]

        with patch("scrapers.fedex_standings.load_player_roster", return_value=fedex_players):
            with patch("scrapers.player_matcher.load_players_from_tournament_results", return_value=tournament_players):
                players = load_all_espn_players()

        assert len(players) == 2
        athlete_ids = {p["athlete_id"] for p in players}
        assert "9478" in athlete_ids
        assert "5860" in athlete_ids

    def test_deduplicates(self):
        """Same player in both sources only appears once."""
        fedex_players = [
            {"athlete_id": "9478", "name": "Scottie Scheffler"},
        ]
        tournament_players = [
            {"athlete_id": "9478", "name": "Scottie Scheffler"},  # Same player
            {"athlete_id": "5860", "name": "Hideki Matsuyama"},
        ]

        with patch("scrapers.fedex_standings.load_player_roster", return_value=fedex_players):
            with patch("scrapers.player_matcher.load_players_from_tournament_results", return_value=tournament_players):
                players = load_all_espn_players()

        assert len(players) == 2
        athlete_ids = [p["athlete_id"] for p in players]
        assert len(athlete_ids) == len(set(athlete_ids))  # No duplicates

    def test_handles_fedex_error(self):
        """Continues loading if fedex standings fails."""
        tournament_players = [
            {"athlete_id": "5860", "name": "Hideki Matsuyama"},
        ]

        with patch("scrapers.fedex_standings.load_player_roster", side_effect=Exception("File not found")):
            with patch("scrapers.player_matcher.load_players_from_tournament_results", return_value=tournament_players):
                players = load_all_espn_players()

        assert len(players) == 1
        assert players[0]["athlete_id"] == "5860"


class TestLookupGolferEspn:
    """Tests for ESPN API lookup."""

    def test_lookup_returns_match(self):
        """Returns match from current tournament field."""
        mock_client = MagicMock()
        mock_client.get_scoreboard.return_value = {
            "events": [{
                "competitions": [{
                    "competitors": [
                        {"id": "9478", "athlete": {"displayName": "Scottie Scheffler"}},
                        {"id": "5860", "athlete": {"displayName": "Hideki Matsuyama"}},
                    ]
                }]
            }]
        }

        name, espn_id, confidence = lookup_golfer_espn("Scottie Scheffler", mock_client)

        assert name == "Scottie Scheffler"
        assert espn_id == "9478"
        assert confidence == 100

    def test_lookup_no_events(self):
        """Returns None when no events in scoreboard."""
        mock_client = MagicMock()
        mock_client.get_scoreboard.return_value = {"events": []}

        name, espn_id, confidence = lookup_golfer_espn("Test Player", mock_client)

        assert name is None
        assert espn_id is None
        assert confidence == 0

    def test_lookup_handles_exception(self):
        """Returns None when API call fails."""
        mock_client = MagicMock()
        mock_client.get_scoreboard.side_effect = Exception("Network error")

        name, espn_id, confidence = lookup_golfer_espn("Test Player", mock_client)

        assert name is None
        assert espn_id is None
        assert confidence == 0


class TestMatchGolfersEnhanced:
    """Tests for enhanced matching with fallback."""

    @pytest.fixture
    def golfers(self):
        return [
            {"golfer_id": 1, "name": "Scottie Scheffler"},
            {"golfer_id": 2, "name": "Unknown Player"},
        ]

    @pytest.fixture
    def espn_players(self):
        return [
            {"athlete_id": "9478", "name": "Scottie Scheffler"},
        ]

    def test_matches_from_local_data(self, golfers, espn_players):
        """Matches golfers against provided local data."""
        results = match_golfers_enhanced(
            golfers, espn_players, lookup_unmatched=False
        )

        assert len(results) == 2
        assert results[0]["espn_id"] == "9478"
        assert results[0]["status"] == "MATCH"
        assert results[1]["status"] == "NO_MATCH"

    def test_falls_back_to_api_lookup(self, golfers, espn_players):
        """Looks up unmatched golfers via ESPN API."""
        mock_client = MagicMock()
        mock_client.get_scoreboard.return_value = {
            "events": [{
                "competitions": [{
                    "competitors": [
                        {"id": "12345", "athlete": {"displayName": "Unknown Player"}},
                    ]
                }]
            }]
        }

        results = match_golfers_enhanced(
            golfers, espn_players, lookup_unmatched=True, client=mock_client
        )

        assert results[1]["espn_id"] == "12345"
        assert results[1]["status"] == "MATCH"

    def test_no_api_lookup_when_disabled(self, golfers, espn_players):
        """Does not call API when lookup_unmatched=False."""
        mock_client = MagicMock()

        results = match_golfers_enhanced(
            golfers, espn_players, lookup_unmatched=False, client=mock_client
        )

        mock_client.get_scoreboard.assert_not_called()
        assert results[1]["status"] == "NO_MATCH"

    def test_loads_all_players_when_not_provided(self):
        """Loads comprehensive player list when espn_players not provided."""
        all_players = [
            {"athlete_id": "9478", "name": "Scottie Scheffler"},
        ]
        golfers = [{"golfer_id": 1, "name": "Scottie Scheffler"}]

        with patch("scrapers.player_matcher.load_all_espn_players", return_value=all_players) as mock_load:
            results = match_golfers_enhanced(golfers, lookup_unmatched=False)

        mock_load.assert_called_once()
        assert results[0]["espn_id"] == "9478"
