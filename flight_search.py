from __future__ import annotations

import logging
import time
from datetime import datetime

import requests

from config import AMADEUS_API_KEY, AMADEUS_API_SECRET, NON_STOP

logger = logging.getLogger(__name__)

TOKEN_ENDPOINT = "https://test.api.amadeus.com/v1/security/oauth2/token"
IATA_ENDPOINT = "https://test.api.amadeus.com/v1/reference-data/locations/cities"
FLIGHT_ENDPOINT = "https://test.api.amadeus.com/v2/shopping/flight-offers"


class FlightSearch:
    """Wrapper around the Amadeus REST API for IATA lookups and flight searches."""

    def __init__(self) -> None:
        self._token: str = self._get_new_token()

    def _get_new_token(self) -> str:
        """Authenticate with Amadeus and return a fresh bearer token."""
        response = requests.post(
            url=TOKEN_ENDPOINT,
            data={
                "grant_type": "client_credentials",
                "client_id": AMADEUS_API_KEY,
                "client_secret": AMADEUS_API_SECRET,
            },
        )
        response.raise_for_status()
        token: str = response.json()["access_token"]
        logger.info("Successfully obtained Amadeus access token.")
        return token

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def _request_with_refresh(
        self, method: str, url: str, **kwargs
    ) -> requests.Response:
        """Make an authenticated request with token refresh and rate-limit retry.

        - 401: refresh the bearer token and retry once.
        - 429: back off for the duration specified in Retry-After (default 5 s)
               and retry once before giving up.
        """
        response = requests.request(method, url, headers=self._auth_headers(), **kwargs)

        if response.status_code == 401:
            logger.info("Token expired — refreshing Amadeus token.")
            self._token = self._get_new_token()
            response = requests.request(method, url, headers=self._auth_headers(), **kwargs)

        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            logger.warning("Rate limited by Amadeus — waiting %d s before retry.", retry_after)
            time.sleep(retry_after)
            response = requests.request(method, url, headers=self._auth_headers(), **kwargs)

        response.raise_for_status()
        return response

    def get_destination_code(self, city_name: str) -> str:
        """Return the IATA city code for *city_name*, or an empty string on failure."""
        params = {"keyword": city_name, "max": "2", "include": "AIRPORTS"}
        try:
            response = self._request_with_refresh("GET", IATA_ENDPOINT, params=params)
            results: list[dict] = response.json()["data"]
            if not results:
                logger.warning("No IATA code found for city '%s'.", city_name)
                return ""
            code: str = results[0]["iataCode"]
            logger.info("Resolved '%s' → IATA code '%s'.", city_name, code)
            return code
        except (requests.HTTPError, KeyError, IndexError) as exc:
            logger.error("Failed to get IATA code for '%s': %s", city_name, exc)
            return ""

    def check_flights(
        self,
        origin_city_code: str,
        destination_city_code: str,
        from_time: datetime,
        to_time: datetime,
    ) -> dict:
        """Search for the cheapest round-trip flights between two IATA codes.

        Args:
            origin_city_code: IATA code of the departure city.
            destination_city_code: IATA code of the arrival city.
            from_time: Earliest departure date to search.
            to_time: Latest return date to search.

        Returns:
            Raw Amadeus flight-offers JSON, or an empty dict on failure.
        """
        params = {
            "originLocationCode": origin_city_code,
            "destinationLocationCode": destination_city_code,
            "departureDate": from_time.strftime("%Y-%m-%d"),
            "returnDate": to_time.strftime("%Y-%m-%d"),
            "adults": 1,
            "nonStop": NON_STOP,
            "currencyCode": "USD",
            "max": "10",
        }
        try:
            response = self._request_with_refresh("GET", FLIGHT_ENDPOINT, params=params)
            return response.json()
        except requests.HTTPError as exc:
            logger.error(
                "Flight search failed for %s → %s: %s",
                origin_city_code,
                destination_city_code,
                exc,
            )
            return {}
