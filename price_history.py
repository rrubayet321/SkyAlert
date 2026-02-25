"""price_history.py — SQLite price history log.

Every flight search result is appended to a local SQLite database so that
price trends can be queried over time.  Uses only the Python standard library
(no extra dependencies).

Schema
------
    CREATE TABLE IF NOT EXISTS price_history (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        searched_at   TEXT NOT NULL,          -- ISO-8601 UTC timestamp
        origin        TEXT NOT NULL,          -- IATA code
        destination   TEXT NOT NULL,          -- IATA code
        destination_city TEXT NOT NULL,
        price         REAL,                   -- NULL when no flights found
        out_date      TEXT,
        return_date   TEXT,
        is_deal       INTEGER NOT NULL DEFAULT 0  -- 1 when price beat threshold
    );
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flight_data import FlightData

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "price_history.db"


def _get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    """Create the price_history table if it does not exist."""
    with _get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS price_history (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                searched_at      TEXT    NOT NULL,
                origin           TEXT    NOT NULL,
                destination      TEXT    NOT NULL,
                destination_city TEXT    NOT NULL,
                price            REAL,
                out_date         TEXT,
                return_date      TEXT,
                is_deal          INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    logger.info("Price history DB ready at %s.", db_path)


def record(
    origin: str,
    flight: FlightData,
    is_deal: bool = False,
    db_path: Path = DB_PATH,
) -> None:
    """Append one search result row to the price_history table.

    Args:
        origin: IATA code of the departure city used in the search.
        flight: The FlightData result (valid or not).
        is_deal: True when this result triggered an alert.
        db_path: Override the default DB path (useful in tests).
    """
    price = float(flight.price) if flight.is_valid else None
    now = datetime.now(timezone.utc).isoformat()

    with _get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO price_history
                (searched_at, origin, destination, destination_city,
                 price, out_date, return_date, is_deal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                origin,
                flight.destination_airport,
                flight.destination_city,
                price,
                flight.out_date if flight.is_valid else None,
                flight.return_date if flight.is_valid else None,
                int(is_deal),
            ),
        )
    logger.debug(
        "Recorded %s → %s: %s (deal=%s)",
        origin,
        flight.destination_city,
        price,
        is_deal,
    )


def get_history(
    origin: str | None = None,
    destination: str | None = None,
    limit: int = 100,
    db_path: Path = DB_PATH,
) -> list[dict]:
    """Query recent price history rows, optionally filtered by route.

    Args:
        origin: Filter by origin IATA code (optional).
        destination: Filter by destination IATA code (optional).
        limit: Maximum number of rows to return (newest first).
        db_path: Override the default DB path (useful in tests).

    Returns:
        List of dicts with keys matching the price_history columns.
    """
    clauses: list[str] = []
    params: list[str | int] = []

    if origin:
        clauses.append("origin = ?")
        params.append(origin)
    if destination:
        clauses.append("destination = ?")
        params.append(destination)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT * FROM price_history {where} ORDER BY searched_at DESC LIMIT ?"
    params.append(limit)

    with _get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]
