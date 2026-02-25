from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

NA = "N/A"


@dataclass
class FlightData:
    price: float | str
    origin_city: str
    origin_airport: str
    destination_city: str
    destination_airport: str
    out_date: str
    return_date: str

    @property
    def is_valid(self) -> bool:
        return self.price != NA

    def summary(self) -> str:
        return (
            f"${self.price} | {self.origin_city} ({self.origin_airport}) → "
            f"{self.destination_city} ({self.destination_airport}) | "
            f"Out: {self.out_date} | Return: {self.return_date}"
        )


def find_cheapest_flight(
    data: dict,
    origin_city: str = "",
    destination_city: str = "",
) -> FlightData:
    """Return the cheapest round-trip flight from an Amadeus flight-offers response.

    Args:
        data: Raw JSON dict returned by the Amadeus flight-offers endpoint.
        origin_city: Human-readable origin city name (e.g. "Dhaka").
        destination_city: Human-readable destination city name (e.g. "London").

    Returns:
        A FlightData instance. ``price`` is set to ``"N/A"`` when no flights
        are found so callers can check ``flight.is_valid``.
    """
    _empty = FlightData(NA, NA, NA, NA, NA, NA, NA)

    if not data or not data.get("data"):
        logger.warning("No flight data returned from Amadeus.")
        return _empty

    flights = data["data"]

    try:
        cheapest = min(flights, key=lambda x: float(x["price"]["grandTotal"]))
    except (KeyError, ValueError) as exc:
        logger.error("Could not parse flight prices: %s", exc)
        return _empty

    try:
        first_seg = cheapest["itineraries"][0]["segments"][0]
        last_seg = cheapest["itineraries"][0]["segments"][-1]

        origin_iata: str = first_seg["departure"]["iataCode"]
        destination_iata: str = last_seg["arrival"]["iataCode"]
        out_date: str = first_seg["departure"]["at"].split("T")[0]

        return_date = NA
        if len(cheapest["itineraries"]) > 1:
            return_seg = cheapest["itineraries"][1]["segments"][0]
            return_date = return_seg["departure"]["at"].split("T")[0]

        return FlightData(
            price=float(cheapest["price"]["grandTotal"]),
            origin_city=origin_city or origin_iata,
            origin_airport=origin_iata,
            destination_city=destination_city or destination_iata,
            destination_airport=destination_iata,
            out_date=out_date,
            return_date=return_date,
        )

    except (KeyError, IndexError) as exc:
        logger.error("Unexpected Amadeus response structure: %s", exc)
        return _empty
