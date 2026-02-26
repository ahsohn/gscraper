"""Tests for player_matcher module."""

import pytest
from scrapers.player_matcher import normalize_name, find_best_match, match_golfers


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
