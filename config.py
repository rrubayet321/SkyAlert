import os
from dotenv import load_dotenv

load_dotenv()

SHEETY_PRICES_ENDPOINT: str = os.getenv("SHEETY_PRICES_ENDPOINT", "")
SHEETY_USERS_ENDPOINT: str = os.getenv("SHEETY_USERS_ENDPOINT", "")

AMADEUS_API_KEY: str = os.getenv("AMADEUS_API_KEY", "")
AMADEUS_API_SECRET: str = os.getenv("AMADEUS_API_SECRET", "")

MY_EMAIL: str = os.getenv("MY_EMAIL", "")
MY_APP_PASSWORD: str = os.getenv("MY_APP_PASSWORD", "")

ORIGIN_CITY_IATA: str = os.getenv("ORIGIN_CITY_IATA", "LON")
NON_STOP: str = os.getenv("NON_STOP", "false")
