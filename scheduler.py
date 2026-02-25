"""scheduler.py — long-running daily scheduler for SkyAlert.

Runs the full flight-deal search once per day at a configurable time,
keeping the process alive between runs.

Usage
-----
    python scheduler.py                 # runs at 09:00 local time every day
    python scheduler.py --time 06:30    # runs at 06:30 every day
    python scheduler.py --interval 12   # runs every 12 hours instead

Environment
-----------
The scheduler respects the same .env file as main.py.  Make sure all
credentials are configured before starting.
"""

from __future__ import annotations

import argparse
import logging
import time

import schedule

from main import main as run_search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_RUN_TIME = "09:00"


def _job() -> None:
    logger.info("Scheduled run starting…")
    try:
        run_search()
    except Exception as exc:
        logger.error("Scheduled run failed: %s", exc, exc_info=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SkyAlert scheduler — run flight searches on a daily schedule."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--time",
        default=DEFAULT_RUN_TIME,
        metavar="HH:MM",
        help=f"Time of day to run the search (24-h, default: {DEFAULT_RUN_TIME}).",
    )
    group.add_argument(
        "--interval",
        type=int,
        metavar="HOURS",
        help="Run every N hours instead of at a fixed daily time.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.interval:
        schedule.every(args.interval).hours.do(_job)
        logger.info("Scheduler armed: running every %d hour(s).", args.interval)
    else:
        schedule.every().day.at(args.time).do(_job)
        logger.info("Scheduler armed: running daily at %s.", args.time)

    logger.info("Running first search immediately on startup…")
    _job()

    logger.info("Scheduler is running. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
