"""SkyAlert — automated flight deal tracker.

Reads destination targets from a Google Sheet, searches for cheap flights via
the Amadeus API, and sends email alerts when a price beats the target threshold.

Usage
-----
    python main.py              # normal run — sends alerts
    python main.py --dry-run    # searches and prints deals, no alerts sent
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta

from config import ORIGIN_CITY_IATA
from data_manager import DataManager
from flight_data import find_cheapest_flight
from flight_search import FlightSearch
from notification_manager import NotificationManager
from price_history import init_db, record

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SkyAlert: search for cheap flights and send deal alerts."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Search for deals and print results without sending any notifications.",
    )
    return parser.parse_args()


def build_alert_message(cheapest_flight) -> str:
    return (
        f"Low price alert! Only ${cheapest_flight.price} to fly\n"
        f"from {cheapest_flight.origin_city} ({cheapest_flight.origin_airport}) "
        f"to {cheapest_flight.destination_city} ({cheapest_flight.destination_airport}).\n"
        f"Outbound: {cheapest_flight.out_date}\n"
        f"Return:   {cheapest_flight.return_date}"
    )


def main() -> None:
    args = parse_args()

    if args.dry_run:
        logger.info("=== DRY RUN — no alerts will be sent ===")

    init_db()

    data_manager = DataManager()
    flight_search = FlightSearch()
    notification_manager = NotificationManager()

    # Step 1: Load destinations from Google Sheet
    sheet_data = data_manager.get_destination_data()
    if not sheet_data:
        logger.error("No destination data found in sheet. Exiting.")
        sys.exit(1)

    # Step 2: Resolve missing IATA codes and write them back to the sheet
    for row in sheet_data:
        if row["iataCode"] == "":
            code = flight_search.get_destination_code(row["city"])
            if code:
                row["iataCode"] = code
                data_manager.update_destination_codes(row["id"], code)
            else:
                logger.warning("Could not resolve IATA code for '%s' — skipping.", row["city"])

    # Step 3: Load registered users (for multi-user email alerts)
    users = data_manager.get_user_data()
    recipient_emails: list[str] = [u["email"] for u in users if u.get("email")]
    if not recipient_emails:
        logger.info("No registered users found — alerts will go to the account owner.")

    # Step 4: Search flights and alert on deals
    tomorrow = datetime.now() + timedelta(days=1)
    six_months_later = datetime.now() + timedelta(days=180)

    deals_found = 0
    for destination in sheet_data:
        if not destination["iataCode"]:
            continue

        logger.info("Searching flights to %s (%s)…", destination["city"], destination["iataCode"])

        flight_data = flight_search.check_flights(
            origin_city_code=ORIGIN_CITY_IATA,
            destination_city_code=destination["iataCode"],
            from_time=tomorrow,
            to_time=six_months_later,
        )

        cheapest_flight = find_cheapest_flight(
            flight_data,
            origin_city=ORIGIN_CITY_IATA,
            destination_city=destination["city"],
        )

        if not cheapest_flight.is_valid:
            logger.info("No flights found to %s.", destination["city"])
            record(ORIGIN_CITY_IATA, cheapest_flight)
            continue

        logger.info(cheapest_flight.summary())

        is_deal = cheapest_flight.price < destination["lowestPrice"]
        record(ORIGIN_CITY_IATA, cheapest_flight, is_deal=is_deal)

        if is_deal:
            deals_found += 1
            message = build_alert_message(cheapest_flight)

            if args.dry_run:
                print(f"\n{'='*50}\nDEAL FOUND:\n{message}\n{'='*50}")
            else:
                notification_manager.send_emails(
                    message,
                    recipient_list=recipient_emails or None,
                    flight=cheapest_flight,
                )

    logger.info("Search complete. %d deal(s) found.", deals_found)


if __name__ == "__main__":
    main()
