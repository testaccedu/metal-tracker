import os
import httpx
from datetime import datetime, timedelta
from typing import Optional
from functools import lru_cache

METALS_API_KEY = os.getenv("METALS_API_KEY", "")
CACHE_DURATION_MINUTES = 5

# Cache fuer Preise
_price_cache: dict = {}
_cache_timestamp: Optional[datetime] = None

# Gramm pro Feinunze
GRAMS_PER_OZ = 31.1035

# Metal API Symbole
METAL_SYMBOLS = {
    "gold": "XAU",
    "silver": "XAG",
    "platinum": "XPT",
    "palladium": "XPD"
}


async def fetch_live_prices() -> dict[str, float]:
    """Holt aktuelle Preise von der Metals API (metals.dev)"""
    global _price_cache, _cache_timestamp

    # Cache pruefen
    if _cache_timestamp and datetime.now() - _cache_timestamp < timedelta(minutes=CACHE_DURATION_MINUTES):
        return _price_cache

    if not METALS_API_KEY:
        # Fallback: Statische Demo-Preise (USD pro Unze)
        return get_fallback_prices()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.metals.dev/v1/latest",
                params={
                    "api_key": METALS_API_KEY,
                    "currency": "EUR",
                    "unit": "g"
                },
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()

            prices = {}
            metals_data = data.get("metals", {})

            for metal, symbol in METAL_SYMBOLS.items():
                if symbol.lower() in metals_data:
                    prices[metal] = metals_data[symbol.lower()]

            _price_cache = prices
            _cache_timestamp = datetime.now()
            return prices

    except Exception as e:
        print(f"Fehler beim Abrufen der Preise: {e}")
        return get_fallback_prices()


def get_fallback_prices() -> dict[str, float]:
    """Fallback-Preise falls API nicht verfuegbar (EUR pro Gramm, Stand ~2024)"""
    return {
        "gold": 75.50,
        "silver": 0.92,
        "platinum": 28.50,
        "palladium": 29.80
    }


async def get_price_per_gram(metal_type: str) -> float:
    """Gibt den aktuellen Preis pro Gramm in EUR zurueck"""
    prices = await fetch_live_prices()
    return prices.get(metal_type.lower(), 0.0)


async def get_all_prices() -> dict[str, dict]:
    """Gibt alle Preise mit Details zurueck"""
    prices = await fetch_live_prices()
    result = {}

    for metal, price_per_gram in prices.items():
        result[metal] = {
            "price_per_gram_eur": round(price_per_gram, 4),
            "price_per_oz_eur": round(price_per_gram * GRAMS_PER_OZ, 2),
            "timestamp": _cache_timestamp or datetime.now()
        }

    return result


async def calculate_current_value(metal_type: str, weight_grams: float) -> float:
    """Berechnet den aktuellen Wert einer Position"""
    price_per_gram = await get_price_per_gram(metal_type)
    return round(price_per_gram * weight_grams, 2)
