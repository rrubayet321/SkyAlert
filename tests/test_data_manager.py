"""Unit tests for data_manager.py — all HTTP calls are mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from data_manager import DataManager


PRICES_URL = "https://api.sheety.co/test/sheet/prices"
USERS_URL = "https://api.sheety.co/test/sheet/users"

PRICES_PAYLOAD = {
    "prices": [
        {"id": 1, "city": "London", "iataCode": "LHR", "lowestPrice": 300},
        {"id": 2, "city": "Tokyo", "iataCode": "", "lowestPrice": 500},
    ]
}

USERS_PAYLOAD = {
    "users": [
        {"firstName": "Jane", "lastName": "Doe", "email": "jane@example.com"},
    ]
}


@pytest.fixture()
def manager(monkeypatch):
    monkeypatch.setattr("data_manager.SHEETY_PRICES_ENDPOINT", PRICES_URL)
    monkeypatch.setattr("data_manager.SHEETY_USERS_ENDPOINT", USERS_URL)
    return DataManager()


class TestGetDestinationData:
    def test_returns_prices_list_on_success(self, manager):
        mock_resp = MagicMock()
        mock_resp.json.return_value = PRICES_PAYLOAD
        mock_resp.raise_for_status.return_value = None

        with patch("data_manager.requests.get", return_value=mock_resp):
            result = manager.get_destination_data()

        assert len(result) == 2
        assert result[0]["city"] == "London"

    def test_returns_empty_list_on_http_error(self, manager):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("500")

        with patch("data_manager.requests.get", return_value=mock_resp):
            result = manager.get_destination_data()

        assert result == []

    def test_stores_data_on_instance(self, manager):
        mock_resp = MagicMock()
        mock_resp.json.return_value = PRICES_PAYLOAD
        mock_resp.raise_for_status.return_value = None

        with patch("data_manager.requests.get", return_value=mock_resp):
            manager.get_destination_data()

        assert len(manager.destination_data) == 2


class TestUpdateDestinationCodes:
    def test_sends_put_with_correct_body(self, manager, monkeypatch):
        monkeypatch.setattr("data_manager.SHEETY_PRICES_ENDPOINT", PRICES_URL)
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None

        with patch("data_manager.requests.put", return_value=mock_resp) as mock_put:
            manager.update_destination_codes(row_id=2, new_code="NRT")

        mock_put.assert_called_once_with(
            url=f"{PRICES_URL}/2",
            json={"price": {"iataCode": "NRT"}},
        )


class TestGetUserData:
    def test_returns_users_list_on_success(self, manager):
        mock_resp = MagicMock()
        mock_resp.json.return_value = USERS_PAYLOAD
        mock_resp.raise_for_status.return_value = None

        with patch("data_manager.requests.get", return_value=mock_resp):
            result = manager.get_user_data()

        assert len(result) == 1
        assert result[0]["email"] == "jane@example.com"

    def test_returns_empty_list_when_endpoint_not_set(self, manager, monkeypatch):
        monkeypatch.setattr("data_manager.SHEETY_USERS_ENDPOINT", "")
        result = manager.get_user_data()
        assert result == []

    def test_returns_empty_list_on_http_error(self, manager):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("404")

        with patch("data_manager.requests.get", return_value=mock_resp):
            result = manager.get_user_data()

        assert result == []
