"""dashboard.py — SkyAlert price history web dashboard.

Serves a lightweight Flask web app that queries the local SQLite price history
database and renders interactive Chart.js charts for each tracked destination.

Usage
-----
    python dashboard.py              # http://127.0.0.1:5050
    python dashboard.py --port 8080  # custom port
    python dashboard.py --host 0.0.0.0 --port 5050  # expose on the network

The dashboard is read-only and performs no writes to the database.
Intended for local or private-network use; do not expose to the public internet
without adding authentication.
"""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict

from flask import Flask, jsonify, render_template

from price_history import get_history

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    """Serve the main dashboard page."""
    return render_template("dashboard.html")


@app.route("/api/history")
def api_history():
    """Return all price history rows grouped by destination city.

    Response shape:
        {
            "London": [
                {"date": "2026-02-20", "price": 420.0, "is_deal": false, ...},
                ...
            ],
            ...
        }
    """
    rows = get_history(limit=2000)

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["destination_city"]].append(
            {
                "date": row["searched_at"][:10],
                "price": row["price"],
                "is_deal": bool(row["is_deal"]),
                "out_date": row["out_date"],
                "return_date": row["return_date"],
            }
        )

    # Sort each destination's entries chronologically (oldest → newest)
    for city in grouped:
        grouped[city].sort(key=lambda r: r["date"])

    return jsonify(dict(grouped))


@app.route("/api/stats")
def api_stats():
    """Return aggregate statistics across all recorded searches.

    Response shape:
        {
            "total_searches": 120,
            "deals_found": 7,
            "destinations_tracked": 5,
            "cheapest_ever": 312.0
        }
    """
    rows = get_history(limit=10_000)

    valid_prices = [r["price"] for r in rows if r["price"] is not None]

    return jsonify(
        {
            "total_searches": len(rows),
            "deals_found": sum(1 for r in rows if r["is_deal"]),
            "destinations_tracked": len({r["destination_city"] for r in rows}),
            "cheapest_ever": min(valid_prices) if valid_prices else None,
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SkyAlert dashboard — visualise your price history locally."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1). Use 0.0.0.0 for LAN access.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5050,
        help="Port to listen on (default: 5050).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    logger.info("SkyAlert dashboard → http://%s:%s", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=False)
