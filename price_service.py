import httpx
from datetime import datetime, timedelta
from typing import Optional

# Preisquelle: GOLD.DE API (https://api.edelmetalle.de)
# Copyright: GOLD.DE - Preise ohne Gewaehr

CACHE_DURATION_MINUTES = 5
# HINWEIS: Discounts werden direkt in den User-Settings konfiguriert (default_discount_*)

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
                    # Spot-Preis ohne Abschlag (Discounts werden per User-Settings angewendet)
                    prices[metal] = price_per_gram

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
    """Fallback-Preise falls API nicht verfuegbar (EUR pro Gramm, Spot-Preis)"""
    return {
        "gold": 118.50,      # Spot-Preis Gold
        "silver": 1.96,      # Spot-Preis Silber
        "platinum": 56.15,   # Spot-Preis Platin
        "palladium": 44.20   # Spot-Preis Palladium
    }


async def get_price_per_gram(metal_type: str) -> float:
    """Gibt den aktuellen Spot-Preis pro Gramm in EUR zurueck"""
    prices = await fetch_live_prices()
    return prices.get(metal_type.lower(), 0.0)


async def get_all_prices() -> dict[str, dict]:
    """Gibt alle Preise mit Details zurueck"""
    prices = await fetch_live_prices()
    result = {}

    for metal, spot_per_gram in prices.items():
        result[metal] = {
            "spot_per_gram_eur": round(spot_per_gram, 4),
            "spot_per_oz_eur": round(spot_per_gram * GRAMS_PER_OZ, 2),
            "timestamp": _cache_timestamp or datetime.now()
        }

    return result


async def calculate_current_value(metal_type: str, weight_grams: float, discount_percent: float = 0.0) -> float:
    """
    Berechnet den aktuellen Wert einer Position basierend auf Spot-Preis minus Discount

    Args:
        metal_type: Art des Edelmetalls (gold, silver, platinum, palladium)
        weight_grams: Gewicht in Gramm
        discount_percent: Abschlag vom Spot-Preis in Prozent (z.B. 5.0 fuer 5%)

    Returns:
        Aktueller Wert in EUR (Spot-Preis minus Discount)
    """
    spot_price_per_gram = await get_price_per_gram(metal_type)

    # Abschlag vom Spot-Preis anwenden (z.B. 5% Abschlag -> Faktor 0.95)
    if discount_percent > 0:
        spot_price_per_gram = spot_price_per_gram * (1 - discount_percent / 100)

    return round(spot_price_per_gram * weight_grams, 2)


def get_source_info() -> dict:
    """Gibt Informationen zur Preisquelle zurueck"""
    return {
        "source": "GOLD.DE",
        "api_url": "https://api.edelmetalle.de/public.json",
        "copyright": "Preise von GOLD.DE - ohne Gewaehr",
        "price_type": "Spot-Preis (Discounts werden per User-Settings angewendet)",
        "cache_minutes": CACHE_DURATION_MINUTES
    }
