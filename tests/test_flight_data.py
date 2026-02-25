"""Unit tests for flight_data.py — no network calls, no external dependencies."""

import pytest

from flight_data import FlightData, find_cheapest_flight

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_flight(
    grand_total: str,
    origin_iata: str = "DAC",
    destination_iata: str = "LHR",
    dep_at: str = "2025-06-01T08:00:00",
    ret_at: str = "2025-06-15T10:00:00",
) -> dict:
    """Build a minimal Amadeus flight-offers 'data' item."""
    return {
        "price": {"grandTotal": grand_total},
        "itineraries": [
            {
                "segments": [
                    {
                        "departure": {"iataCode": origin_iata, "at": dep_at},
                        "arrival": {"iataCode": destination_iata, "at": dep_at},
                    }
                ]
            },
            {
                "segments": [
                    {
                        "departure": {"iataCode": destination_iata, "at": ret_at},
                        "arrival": {"iataCode": origin_iata, "at": ret_at},
                    }
                ]
            },
        ],
    }


SAMPLE_RESPONSE = {
    "data": [
        _make_flight("850.00"),
        _make_flight("620.00"),
        _make_flight("999.99"),
    ]
}


# ---------------------------------------------------------------------------
# FlightData dataclass tests
# ---------------------------------------------------------------------------


class TestFlightData:
    def test_is_valid_with_price(self):
        flight = FlightData(
            price=450.0,
            origin_city="Dhaka",
            origin_airport="DAC",
            destination_city="London",
            destination_airport="LHR",
            out_date="2025-06-01",
            return_date="2025-06-15",
        )
        assert flight.is_valid is True

    def test_is_invalid_when_na(self):
        flight = FlightData("N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A")
        assert flight.is_valid is False

    def test_summary_contains_key_fields(self):
        flight = FlightData(
            price=450.0,
            origin_city="Dhaka",
            origin_airport="DAC",
            destination_city="London",
            destination_airport="LHR",
            out_date="2025-06-01",
            return_date="2025-06-15",
        )
        summary = flight.summary()
        assert "450.0" in summary
        assert "DAC" in summary
        assert "LHR" in summary
        assert "Dhaka" in summary
        assert "London" in summary

    def test_dataclass_equality(self):
        f1 = FlightData(500.0, "Dhaka", "DAC", "London", "LHR", "2025-06-01", "2025-06-15")
        f2 = FlightData(500.0, "Dhaka", "DAC", "London", "LHR", "2025-06-01", "2025-06-15")
        assert f1 == f2


# ---------------------------------------------------------------------------
# find_cheapest_flight tests
# ---------------------------------------------------------------------------


class TestFindCheapestFlight:
    def test_returns_cheapest_from_multiple_flights(self):
        result = find_cheapest_flight(SAMPLE_RESPONSE)
        assert result.price == 620.0

    def test_uses_provided_city_names(self):
        result = find_cheapest_flight(
            SAMPLE_RESPONSE, origin_city="Dhaka", destination_city="London"
        )
        assert result.origin_city == "Dhaka"
        assert result.destination_city == "London"

    def test_falls_back_to_iata_when_no_city_name_given(self):
        result = find_cheapest_flight(SAMPLE_RESPONSE)
        assert result.origin_city == "DAC"
        assert result.destination_city == "LHR"

    def test_airport_codes_always_iata(self):
        result = find_cheapest_flight(
            SAMPLE_RESPONSE, origin_city="Dhaka", destination_city="London"
        )
        assert result.origin_airport == "DAC"
        assert result.destination_airport == "LHR"

    def test_out_date_extracted_correctly(self):
        result = find_cheapest_flight(SAMPLE_RESPONSE)
        assert result.out_date == "2025-06-01"

    def test_return_date_extracted_correctly(self):
        result = find_cheapest_flight(SAMPLE_RESPONSE)
        assert result.return_date == "2025-06-15"

    def test_returns_na_flight_when_data_is_none(self):
        result = find_cheapest_flight(None)
        assert result.is_valid is False
        assert result.price == "N/A"

    def test_returns_na_flight_when_data_key_missing(self):
        result = find_cheapest_flight({})
        assert result.is_valid is False

    def test_returns_na_flight_when_data_list_is_empty(self):
        result = find_cheapest_flight({"data": []})
        assert result.is_valid is False

    def test_single_flight_in_response(self):
        single = {"data": [_make_flight("350.00")]}
        result = find_cheapest_flight(single)
        assert result.price == 350.0

    def test_no_return_itinerary_gives_na_return_date(self):
        one_way = {
            "data": [
                {
                    "price": {"grandTotal": "400.00"},
                    "itineraries": [
                        {
                            "segments": [
                                {
                                    "departure": {"iataCode": "DAC", "at": "2025-07-01T06:00:00"},
                                    "arrival": {"iataCode": "LHR", "at": "2025-07-01T18:00:00"},
                                }
                            ]
                        }
                    ],
                }
            ]
        }
        result = find_cheapest_flight(one_way)
        assert result.return_date == "N/A"
        assert result.price == 400.0

    def test_handles_malformed_response_gracefully(self):
        bad_data = {"data": [{"price": {}, "itineraries": []}]}
        result = find_cheapest_flight(bad_data)
        assert result.is_valid is False
