from datetime import date

import pytest

from scripts.validate_payment_document_type_switch import build_window, parse_document_types


def test_build_window_makes_end_date_exclusive():
    assert build_window(date(2026, 8, 1), date(2026, 8, 5)) == (date(2026, 8, 1), date(2026, 8, 6))


def test_build_window_rejects_inverted_range():
    with pytest.raises(ValueError, match="date_to"):
        build_window(date(2026, 8, 5), date(2026, 8, 1))


def test_parse_document_types_deduplicates_and_preserves_order():
    assert parse_document_types(["3", 1, "3"]) == [3, 1]
