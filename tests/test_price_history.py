"""Unit tests for price_history.py — uses a temporary in-memory DB path."""

from __future__ import annotations

import pytest

from flight_data import FlightData
from price_history import get_history, init_db, record

NA = "N/A"

VALID_FLIGHT = FlightData(
    price=450.0,
    origin_city="Dhaka",
    origin_airport="DAC",
    destination_city="London",
    destination_airport="LHR",
    out_date="2025-07-10",
    return_date="2025-07-24",
)

INVALID_FLIGHT = FlightData(NA, NA, NA, NA, NA, NA, NA)


@pytest.fixture()
def tmp_db(tmp_path):
    db_path = tmp_path / "test_history.db"
    init_db(db_path)
    return db_path


class TestInitDb:
    def test_creates_db_file(self, tmp_path):
        db_path = tmp_path / "new.db"
        assert not db_path.exists()
        init_db(db_path)
        assert db_path.exists()

    def test_idempotent_on_second_call(self, tmp_db):
        init_db(tmp_db)  # Should not raise


class TestRecord:
    def test_records_valid_flight(self, tmp_db):
        record("DAC", VALID_FLIGHT, is_deal=True, db_path=tmp_db)
        rows = get_history(db_path=tmp_db)
        assert len(rows) == 1
        assert rows[0]["price"] == 450.0
        assert rows[0]["is_deal"] == 1

    def test_records_invalid_flight_with_null_price(self, tmp_db):
        record("DAC", INVALID_FLIGHT, db_path=tmp_db)
        rows = get_history(db_path=tmp_db)
        assert len(rows) == 1
        assert rows[0]["price"] is None

    def test_is_deal_defaults_to_false(self, tmp_db):
        record("DAC", VALID_FLIGHT, db_path=tmp_db)
        rows = get_history(db_path=tmp_db)
        assert rows[0]["is_deal"] == 0

    def test_multiple_records_stored_independently(self, tmp_db):
        record("DAC", VALID_FLIGHT, db_path=tmp_db)
        record("DAC", VALID_FLIGHT, is_deal=True, db_path=tmp_db)
        rows = get_history(db_path=tmp_db)
        assert len(rows) == 2


class TestGetHistory:
    def test_returns_newest_first(self, tmp_db):
        import time as _time

        record("DAC", VALID_FLIGHT, db_path=tmp_db)
        _time.sleep(0.01)
        flight2 = FlightData(300.0, "Dhaka", "DAC", "Paris", "CDG", "2025-08-01", "2025-08-15")
        record("DAC", flight2, db_path=tmp_db)

        rows = get_history(db_path=tmp_db)
        assert rows[0]["destination_city"] == "Paris"

    def test_filter_by_origin(self, tmp_db):
        record("DAC", VALID_FLIGHT, db_path=tmp_db)
        flight_lon = FlightData(200.0, "London", "LON", "Paris", "CDG", "2025-08-01", "2025-08-10")
        record("LON", flight_lon, db_path=tmp_db)

        rows = get_history(origin="DAC", db_path=tmp_db)
        assert len(rows) == 1
        assert rows[0]["origin"] == "DAC"

    def test_filter_by_destination(self, tmp_db):
        record("DAC", VALID_FLIGHT, db_path=tmp_db)
        flight_cdg = FlightData(200.0, "Dhaka", "DAC", "Paris", "CDG", "2025-08-01", "2025-08-10")
        record("DAC", flight_cdg, db_path=tmp_db)

        rows = get_history(destination="LHR", db_path=tmp_db)
        assert len(rows) == 1
        assert rows[0]["destination"] == "LHR"

    def test_limit_respected(self, tmp_db):
        for _ in range(5):
            record("DAC", VALID_FLIGHT, db_path=tmp_db)

        rows = get_history(limit=3, db_path=tmp_db)
        assert len(rows) == 3

    def test_returns_empty_list_when_no_data(self, tmp_db):
        assert get_history(db_path=tmp_db) == []
