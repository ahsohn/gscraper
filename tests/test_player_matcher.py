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
