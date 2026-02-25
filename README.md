# SkyAlert ✈️

![CI](https://github.com/rrubayet321/SkyAlert/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white)

> **Automated flight deal tracker** — monitors fares for your target destinations around the clock and fires a beautiful HTML email the moment a price drops below your threshold.

---

## What is SkyAlert?

SkyAlert is a self-hosted Python automation tool that removes the tedium of manually checking flight prices. You tell it where you want to go and the maximum price you're willing to pay. It searches the [Amadeus Flight Offers API](https://developers.amadeus.com/self-service/category/flights/api-doc/flight-offers-search) across the next six months, every single day, and emails you the moment a deal appears.

Destinations and registered users live in a Google Sheet — no database admin required. Every search result is also logged to a local SQLite database, giving you a growing price history that you can explore through the included web dashboard.

---

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                      scheduler.py                       │
│           (runs main.py once per day at 09:00)          │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                        main.py                          │
│                                                         │
│  1. Load destinations + price targets  ◄── Google Sheet │
│  2. Resolve missing IATA codes              (via Sheety) │
│  3. Search cheapest round-trip fare    ◄── Amadeus API  │
│  4. Compare fare vs. target price                       │
│  5. Log result to SQLite price history                  │
│  6. Send HTML email alert if deal found ──► Gmail SMTP  │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    dashboard.py                         │
│        (local web UI for price history charts)          │
└─────────────────────────────────────────────────────────┘
```

---

## Features

### Core Automation
- Reads destination cities and price targets from a **Google Sheet** — edit the sheet to add or remove destinations instantly
- Automatically **resolves and back-fills missing IATA codes** on first run
- Searches the **cheapest round-trip fare** across a configurable 6-month window
- Configurable departure city, non-stop filter, and daily run time

### Alerts
- Sends **HTML email alerts** (with plain-text fallback) when a deal is found
- Emails every registered user listed in the **users** tab of your Google Sheet
- Beautiful email template — price, route, and outbound/return dates at a glance

### Price History & Dashboard
- Every search result (deal or not) is **logged to SQLite** — price, route, dates, and whether it triggered an alert
- **Web dashboard** (`python dashboard.py`) shows interactive price trend charts per destination, summary statistics, and a recent deals table — no extra setup required

### Developer Experience
- `--dry-run` mode — prints deals to the terminal without sending any emails
- **Daily scheduler** (`python scheduler.py`) for fully automated, hands-off operation
- **Docker-ready** — run the scheduler as a background service with one command
- **GitHub Actions CI** — runs `pytest` across Python 3.10, 3.11, and 3.12 on every push
- Structured logging, full type hints, and **41 unit tests** with zero network calls

---

## Architecture

```
skyalert/
├── main.py                  # Orchestrates the full search-and-alert flow
├── scheduler.py             # Wraps main.py in a daily/interval schedule
├── dashboard.py             # Flask web dashboard for price history charts
│
├── config.py                # Centralised settings loaded from environment variables
├── data_manager.py          # Sheety API — reads/writes the Google Sheet
├── flight_search.py         # Amadeus API — IATA code lookup + flight search
├── flight_data.py           # FlightData dataclass + find_cheapest_flight()
├── notification_manager.py  # Gmail SMTP + Jinja2 HTML email
├── price_history.py         # SQLite logger — init, record, query
│
├── templates/
│   ├── alert_email.html     # Jinja2 HTML email template
│   └── dashboard.html       # Web dashboard (Chart.js)
│
├── tests/                   # 41 unit tests, all external services mocked
│   ├── test_flight_data.py
│   ├── test_data_manager.py
│   ├── test_notification_manager.py
│   └── test_price_history.py
│
├── .github/workflows/ci.yml # GitHub Actions — lint + test matrix
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml           # ruff + mypy + pytest configuration
├── requirements.txt
└── .env.example             # Environment variable template
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | |
| [Sheety](https://sheety.co) account | Wraps your Google Sheet as a REST API |
| [Amadeus for Developers](https://developers.amadeus.com) account | Free test tier is sufficient |
| Gmail account with an [App Password](https://support.google.com/accounts/answer/185833) | Required for SMTP access |

---

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/rrubayet321/SkyAlert.git
cd skyalert
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in each value:

| Variable | Description |
|---|---|
| `SHEETY_PRICES_ENDPOINT` | Sheety URL for the **prices** sheet tab |
| `SHEETY_USERS_ENDPOINT` | Sheety URL for the **users** sheet tab (optional) |
| `AMADEUS_API_KEY` | Amadeus client ID |
| `AMADEUS_API_SECRET` | Amadeus client secret |
| `MY_EMAIL` | Your Gmail address |
| `MY_APP_PASSWORD` | Your Gmail App Password (not your regular password) |
| `ORIGIN_CITY_IATA` | IATA code of your home airport (e.g. `LON`, `JFK`, `DAC`) |
| `NON_STOP` | `true` for non-stop flights only, `false` for all routes |

### 3. Set up your Google Sheet

Create a Google Sheet and connect it to Sheety. The sheet needs two tabs named exactly **prices** and **users**.

**prices** tab — one row per destination you want to track:

| city | iataCode | lowestPrice |
|---|---|---|
| London | | 200 |
| Tokyo | | 500 |
| Paris | | 150 |

Leave `iataCode` blank — SkyAlert resolves and fills it in automatically on the first run.

**users** tab — everyone who should receive deal alerts *(optional — leave empty to send to the account owner only)*:

| firstName | lastName | email |
|---|---|---|
| Jane | Doe | jane@example.com |
| John | Smith | john@example.com |

---

## Usage

### One-off search

```bash
# Search for deals and send email alerts
python main.py

# Preview deals in the terminal without sending any emails
python main.py --dry-run
```

### Daily scheduler

```bash
# Run at 09:00 every day (default)
python scheduler.py

# Run at a custom time
python scheduler.py --time 06:30

# Run every N hours instead of at a fixed daily time
python scheduler.py --interval 12
```

Example terminal output:

```
2026-02-25 09:00:00 [INFO] __main__ — Searching flights to London (LHR)…
2026-02-25 09:00:01 [INFO] __main__ — $382.0 | DAC (DAC) → London (LHR) | Out: 2026-04-10 | Return: 2026-04-24
2026-02-25 09:00:01 [INFO] __main__ — Searching flights to Tokyo (NRT)…
2026-02-25 09:00:02 [INFO] __main__ — No flights found to Tokyo.
2026-02-25 09:00:02 [INFO] __main__ — Search complete. 1 deal(s) found.
```

---

## Price History Dashboard

After SkyAlert has run at least once, launch the local web dashboard to explore your price data:

```bash
python dashboard.py
# → Open http://localhost:5050 in your browser

# Custom port
python dashboard.py --port 8080
```

The dashboard shows:
- **Summary stats** — total searches run, deals found, destinations tracked, all-time cheapest fare
- **Price trend charts** — one Chart.js line chart per destination showing how fares have moved over time, with deal alerts highlighted
- **Recent deals table** — a quick-glance log of every triggered alert

---

## Docker

Run the scheduler as a persistent background service — no Python installation required on the host:

```bash
# Build and start the scheduler in the background
docker compose up -d

# Stream live logs
docker compose logs -f

# Stop
docker compose down
```

The SQLite price history database is stored in a named Docker volume (`skyalert_data`) and survives container restarts and re-builds.

---

## Running Tests

```bash
pytest tests/ -v
```

41 tests, zero network calls — all external services (Amadeus, Sheety, Gmail) are mocked.

---

## Technologies

| Technology | Purpose |
|---|---|
| Python 3.10+ | Core language |
| [Amadeus Flight Offers API](https://developers.amadeus.com/self-service/category/flights/api-doc/flight-offers-search) | Live flight price data |
| [Sheety](https://sheety.co) | Google Sheets as a REST API |
| Gmail SMTP | HTML email delivery |
| SQLite (stdlib) | Local price history log |
| [Flask](https://flask.palletsprojects.com) | Price history web dashboard |
| [Jinja2](https://jinja.palletsprojects.com) | HTML email and dashboard templates |
| [Chart.js](https://www.chartjs.org) | Interactive price trend charts |
| [schedule](https://schedule.readthedocs.io) | Daily automation scheduler |
| Docker | Containerised deployment |
| GitHub Actions | CI — lint and test on every push |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | Secure credential management |
| [pytest](https://docs.pytest.org) | Unit testing |
| [ruff](https://docs.astral.sh/ruff/) | Linting and formatting |

---

## Contributing

Pull requests are welcome. For significant changes, please open an issue first to discuss what you'd like to change. Make sure all tests pass before submitting:

```bash
pytest tests/ -v
ruff check .
```

---

## License

MIT
