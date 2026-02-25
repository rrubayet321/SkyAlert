"""Unit tests for notification_manager.py — SMTP and Jinja2 are mocked."""

from __future__ import annotations

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from flight_data import FlightData
from notification_manager import NotificationManager

SAMPLE_FLIGHT = FlightData(
    price=450.0,
    origin_city="Dhaka",
    origin_airport="DAC",
    destination_city="London",
    destination_airport="LHR",
    out_date="2025-07-10",
    return_date="2025-07-24",
)

PLAIN_MESSAGE = (
    "Low price alert! Only $450.0 to fly\n"
    "from Dhaka (DAC) to London (LHR).\n"
    "Outbound: 2025-07-10\n"
    "Return:   2025-07-24"
)


@pytest.fixture()
def nm(monkeypatch):
    monkeypatch.setattr("notification_manager.MY_EMAIL", "sender@example.com")
    monkeypatch.setattr("notification_manager.MY_APP_PASSWORD", "secret")
    return NotificationManager()


class TestSendEmails:
    def test_sends_to_single_recipient(self, nm):
        mock_conn = MagicMock()
        mock_smtp_cls = MagicMock(return_value=mock_conn)
        mock_smtp_cls.__enter__ = lambda s: mock_conn
        mock_smtp_cls.__exit__ = MagicMock(return_value=False)

        with patch("notification_manager.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = lambda s: mock_conn
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            nm.send_emails(PLAIN_MESSAGE, recipient_list=["alice@example.com"])

        mock_conn.sendmail.assert_called_once()
        _, kwargs = mock_conn.sendmail.call_args
        assert mock_conn.sendmail.call_args[1]["to_addrs"] == "alice@example.com" or \
               mock_conn.sendmail.call_args[0][1] == "alice@example.com"

    def test_sends_to_multiple_recipients(self, nm):
        recipients = ["alice@example.com", "bob@example.com", "carol@example.com"]
        mock_conn = MagicMock()

        with patch("notification_manager.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = lambda s: mock_conn
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            nm.send_emails(PLAIN_MESSAGE, recipient_list=recipients)

        assert mock_conn.sendmail.call_count == 3

    def test_each_recipient_gets_correct_to_header(self, nm):
        """Verify the To-header is replaced (not accumulated) for each recipient."""
        recipients = ["alice@example.com", "bob@example.com"]
        sent_messages: list[str] = []
        mock_conn = MagicMock()

        def capture_sendmail(from_addr, to_addrs, msg):
            sent_messages.append((to_addrs, msg))

        mock_conn.sendmail.side_effect = capture_sendmail

        with patch("notification_manager.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = lambda s: mock_conn
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            nm.send_emails(PLAIN_MESSAGE, recipient_list=recipients)

        assert len(sent_messages) == 2
        # Each message's To header must contain only its own recipient
        for _to_addr, raw_msg in sent_messages:
            assert raw_msg.count("alice@example.com") + raw_msg.count("bob@example.com") >= 1
            # Crucially: the previous address must not appear in messages after the first
        _, msg_for_bob = sent_messages[1]
        to_lines = [ln for ln in msg_for_bob.splitlines() if ln.startswith("To:")]
        assert len(to_lines) == 1
        assert "alice@example.com" not in to_lines[0]

    def test_falls_back_to_my_email_when_no_recipients(self, nm, monkeypatch):
        monkeypatch.setattr("notification_manager.MY_EMAIL", "owner@example.com")
        mock_conn = MagicMock()

        with patch("notification_manager.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = lambda s: mock_conn
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            nm.send_emails(PLAIN_MESSAGE)

        assert mock_conn.sendmail.call_count == 1

    def test_smtp_exception_is_caught_and_logged(self, nm, caplog):
        import logging

        mock_conn = MagicMock()
        mock_conn.sendmail.side_effect = smtplib.SMTPException("connection refused")

        with patch("notification_manager.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = lambda s: mock_conn
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            with caplog.at_level(logging.ERROR, logger="notification_manager"):
                nm.send_emails(PLAIN_MESSAGE, recipient_list=["x@example.com"])

        assert any("Failed to send email" in r.message for r in caplog.records)

    def test_html_part_attached_when_flight_provided(self, nm):
        sent_messages: list[str] = []
        mock_conn = MagicMock()

        def capture(from_addr, to_addrs, msg):
            sent_messages.append(msg)

        mock_conn.sendmail.side_effect = capture

        with patch("notification_manager.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = lambda s: mock_conn
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            nm.send_emails(
                PLAIN_MESSAGE,
                recipient_list=["alice@example.com"],
                flight=SAMPLE_FLIGHT,
            )

        assert sent_messages, "No messages were captured"
        raw = sent_messages[0]
        assert "text/html" in raw

    def test_plain_text_only_when_no_flight(self, nm):
        sent_messages: list[str] = []
        mock_conn = MagicMock()

        def capture(from_addr, to_addrs, msg):
            sent_messages.append(msg)

        mock_conn.sendmail.side_effect = capture

        with patch("notification_manager.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__ = lambda s: mock_conn
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            nm.send_emails(PLAIN_MESSAGE, recipient_list=["alice@example.com"])

        raw = sent_messages[0]
        assert "text/plain" in raw
