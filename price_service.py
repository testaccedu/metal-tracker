import httpx
from datetime import datetime, timedelta
from typing import Optional

# Preisquelle: GOLD.DE API (https://api.edelmetalle.de)
# Copyright: GOLD.DE - Preise ohne Gewaehr

CACHE_DURATION_MINUTES = 5
ANKAUF_FAKTOR = 0.95  # 95% vom Spot = realistischer Ankaufswert

# Cache fuer Preise
_price_cache: dict = {}
_cache_timestamp: Optional[datetime] = None

# Gramm pro Feinunze
GRAMS_PER_OZ = 31.1035

# Mapping fuer API-Felder
METAL_API_FIELDS = {
    "gold": "gold_eur",
    "silver": "silber_eur",
    "platinum": "platin_eur",
    "palladium": "palladium_eur"
}


async def fetch_live_prices() -> dict[str, float]:
    """Holt aktuelle Spot-Preise von GOLD.DE API (Preise pro Unze)"""
    global _price_cache, _cache_timestamp

    # Cache pruefen
    if _cache_timestamp and datetime.now() - _cache_timestamp < timedelta(minutes=CACHE_DURATION_MINUTES):
        return _price_cache

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.edelmetalle.de/public.json",
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()

            # Preise pro Gramm berechnen (API liefert pro Unze)
            prices = {}
            for metal, api_field in METAL_API_FIELDS.items():
                if api_field in data:
                    price_per_oz = data[api_field]
                    price_per_gram = price_per_oz / GRAMS_PER_OZ
                    # Ankaufspreis = 95% vom Spot
                    prices[metal] = price_per_gram * ANKAUF_FAKTOR

            _price_cache = prices
            _cache_timestamp = datetime.now()
            return prices

    except Exception as e:
        print(f"Fehler beim Abrufen der Preise von GOLD.DE: {e}")
        # Fallback nur wenn Cache leer
        if _price_cache:
            return _price_cache
        return get_fallback_prices()


def get_fallback_prices() -> dict[str, float]:
    """Fallback-Preise falls API nicht verfuegbar (EUR pro Gramm, Ankauf ~95%)"""
    return {
        "gold": 112.50,      # ~118 Spot * 0.95
        "silver": 1.86,      # ~1.96 Spot * 0.95
        "platinum": 53.35,   # ~56.15 Spot * 0.95
        "palladium": 42.00   # ~44.20 Spot * 0.95
    }


async def get_price_per_gram(metal_type: str) -> float:
    """Gibt den aktuellen Ankaufspreis pro Gramm in EUR zurueck"""
    prices = await fetch_live_prices()
    return prices.get(metal_type.lower(), 0.0)


async def get_all_prices() -> dict[str, dict]:
    """Gibt alle Preise mit Details zurueck"""
    prices = await fetch_live_prices()
    result = {}

    for metal, ankauf_per_gram in prices.items():
        spot_per_gram = ankauf_per_gram / ANKAUF_FAKTOR
        result[metal] = {
            "spot_per_gram_eur": round(spot_per_gram, 4),
            "spot_per_oz_eur": round(spot_per_gram * GRAMS_PER_OZ, 2),
            "ankauf_per_gram_eur": round(ankauf_per_gram, 4),
            "ankauf_per_oz_eur": round(ankauf_per_gram * GRAMS_PER_OZ, 2),
            "ankauf_faktor": ANKAUF_FAKTOR,
            "timestamp": _cache_timestamp or datetime.now()
        }

    return result


async def calculate_current_value(metal_type: str, weight_grams: float) -> float:
    """Berechnet den aktuellen Ankaufswert einer Position"""
    price_per_gram = await get_price_per_gram(metal_type)
    return round(price_per_gram * weight_grams, 2)


def get_source_info() -> dict:
    """Gibt Informationen zur Preisquelle zurueck"""
    return {
        "source": "GOLD.DE",
        "api_url": "https://api.edelmetalle.de/public.json",
        "copyright": "Preise von GOLD.DE - ohne Gewaehr",
        "price_type": "Ankaufspreis (95% vom Spot)",
        "cache_minutes": CACHE_DURATION_MINUTES
    }
