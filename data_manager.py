from __future__ import annotations

import logging

import requests

from config import SHEETY_PRICES_ENDPOINT, SHEETY_USERS_ENDPOINT

logger = logging.getLogger(__name__)


class DataManager:
    """Handles all reads and writes to the Google Sheet via the Sheety API."""

    def __init__(self) -> None:
        self.destination_data: list[dict] = []
        self.user_data: list[dict] = []

    def get_destination_data(self) -> list[dict]:
        """Fetch all destination rows (city, IATA code, lowest price)."""
        try:
            response = requests.get(url=SHEETY_PRICES_ENDPOINT)
            response.raise_for_status()
            self.destination_data = response.json()["prices"]
            logger.info("Loaded %d destinations from sheet.", len(self.destination_data))
        except requests.HTTPError as exc:
            logger.error("Failed to fetch destination data: %s", exc)
            self.destination_data = []
        return self.destination_data

    def update_destination_codes(self, row_id: int, new_code: str) -> None:
        """Write a resolved IATA code back to the sheet for a destination row."""
        update_endpoint = f"{SHEETY_PRICES_ENDPOINT}/{row_id}"
        body = {"price": {"iataCode": new_code}}
        response = requests.put(url=update_endpoint, json=body)
        response.raise_for_status()
        logger.info("Updated row %d with IATA code '%s'.", row_id, new_code)

    def get_user_data(self) -> list[dict]:
        """Fetch all registered users (name, email) from the users sheet tab.

        Falls back gracefully when the users tab does not exist yet, so the app
        still works with a single-tab sheet.
        """
        if not SHEETY_USERS_ENDPOINT:
            logger.warning("SHEETY_USERS_ENDPOINT not set — skipping user lookup.")
            return []
        try:
            response = requests.get(url=SHEETY_USERS_ENDPOINT)
            response.raise_for_status()
            self.user_data = response.json().get("users", [])
            logger.info("Loaded %d registered users.", len(self.user_data))
        except requests.HTTPError as exc:
            logger.warning("Could not fetch user data: %s", exc)
            self.user_data = []
        return self.user_data
