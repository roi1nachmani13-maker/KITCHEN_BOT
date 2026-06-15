"""
Tests for the Hebrew NLP parser.
"""
from __future__ import annotations

import pytest
from src.nlp.parser import MessageParser, ParsedMessage
from src.nlp.intents import Intent


PRODUCTS = ["חלב", "עגבניות", "מוצרלה", "בזיליקום", "שמן זית", "ביצים", "שום"]


@pytest.fixture
def parser():
    p = MessageParser(product_names=PRODUCTS)
    return p


class TestAddIntent:
    def test_bare_product(self, parser):
        r = parser.parse("חלב")
        assert r is not None
        assert r.intent == Intent.ADD
        assert r.product_name == "חלב"
        assert r.quantity == 1.0

    def test_product_with_quantity(self, parser):
        r = parser.parse("חלב 2")
        assert r.intent == Intent.ADD
        assert r.product_name == "חלב"
        assert r.quantity == 2.0

    def test_product_with_float_quantity(self, parser):
        r = parser.parse("שמן זית 1.5")
        assert r.quantity == 1.5

    def test_tsarich_prefix(self, parser):
        r = parser.parse("צריך חלב")
        assert r.intent == Intent.ADD
        assert r.product_name == "חלב"

    def test_tsarich_prefix_with_qty(self, parser):
        r = parser.parse("צריך חלב 3")
        assert r.intent == Intent.ADD
        assert r.quantity == 3.0

    def test_chaser_prefix(self, parser):
        r = parser.parse("חסר מוצרלה")
        assert r.intent == Intent.ADD
        assert r.product_name == "מוצרלה"

    def test_tosif_prefix(self, parser):
        r = parser.parse("תוסיף עגבניות 5")
        assert r.intent == Intent.ADD
        assert r.product_name == "עגבניות"
        assert r.quantity == 5.0

    def test_product_with_unit(self, parser):
        r = parser.parse("עגבניות 5 קג")
        assert r.quantity == 5.0
        assert r.unit == 'ק"ג'

    def test_default_quantity_is_one(self, parser):
        r = parser.parse("בזיליקום")
        assert r.quantity == 1.0


class TestDoneIntent:
    def test_kaniti(self, parser):
        r = parser.parse("קניתי חלב")
        assert r.intent == Intent.MARK_DONE
        assert r.product_name == "חלב"

    def test_higi_a(self, parser):
        r = parser.parse("הגיע חלב")
        assert r.intent == Intent.MARK_DONE

    def test_huvati(self, parser):
        r = parser.parse("הבאתי ביצים")
        assert r.intent == Intent.MARK_DONE
        assert r.product_name == "ביצים"

    def test_hushlam(self, parser):
        r = parser.parse("הושלם בזיליקום")
        assert r.intent == Intent.MARK_DONE


class TestCancelIntent:
    def test_lo_tsarich(self, parser):
        r = parser.parse("לא צריך חלב")
        assert r.intent == Intent.CANCEL
        assert r.product_name == "חלב"

    def test_batel(self, parser):
        r = parser.parse("בטל גבינה")
        assert r.intent == Intent.CANCEL

    def test_timchak(self, parser):
        r = parser.parse("תמחק עגבניות")
        assert r.intent == Intent.CANCEL


class TestRestoreIntent:
    def test_hachzer(self, parser):
        r = parser.parse("החזר חלב")
        assert r.intent == Intent.RESTORE
        assert r.product_name == "חלב"

    def test_tishzor(self, parser):
        r = parser.parse("תשחזר מוצרלה")
        assert r.intent == Intent.RESTORE


class TestFuzzyMatching:
    def test_typo_single_letter(self, parser):
        r = parser.parse("חלאב")  # typo
        assert r is not None
        assert r.matched_name == "חלב"

    def test_typo_mozarella(self, parser):
        r = parser.parse("מוצרלהה")  # extra letter
        assert r.matched_name == "מוצרלה"

    def test_command_ignored(self, parser):
        r = parser.parse("/רשימה")
        assert r is None

    def test_empty_string(self, parser):
        r = parser.parse("")
        assert r is None
