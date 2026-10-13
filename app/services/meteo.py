"""Météo : prévisions des prochains jours et climat à l'année (Open-Meteo).

Source : https://open-meteo.com, sans clé, usage non commercial,
moins de 10 000 appels par jour. Données sous licence CC BY 4.0.

- Les prévisions sont demandées en direct (gardées 1 h en mémoire).
- Le climat est précalculé par scripts/preparer_climat.py dans
  data/climat_mensuel.csv, pour ne pas interroger l'historique à chaque visite.
"""
import pandas as pd

from .outils import DOSSIER_DATA, cache_ttl, get_json

API_PREVISIONS = "https://api.open-meteo.com/v1/forecast"
FICHIER_CLIMAT = DOSSIER_DATA / "climat_mensuel.csv"
VARIABLES_JOUR = "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code"


@cache_ttl(3600)
def previsions(lat: float, lon: float, jours: int = 7) -> dict | None:
    data = get_json(
        API_PREVISIONS,
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": VARIABLES_JOUR,
            "timezone": "auto",  # heure locale, utile pour les villes d'outre-mer
            "forecast_days": jours,
        },
    )
    if not data or "daily" not in data:
        return None
    jour = data["daily"]
    return {
        "dates": jour["time"],
        "tmax": jour["temperature_2m_max"],
        "tmin": jour["temperature_2m_min"],
        "pluie_mm": jour["precipitation_sum"],
        "code_meteo": jour["weather_code"],
    }


@cache_ttl(24 * 3600)
def _table_climat() -> pd.DataFrame | None:
    if not FICHIER_CLIMAT.exists():
        return None
    return pd.read_csv(FICHIER_CLIMAT, dtype={"code": str})


def climat_mensuel(code: str) -> pd.DataFrame | None:
    """Moyennes par mois (colonnes : mois, temp_moy, precip_mm, soleil_h)."""
    table = _table_climat()
    if table is None:
        return None
    ville = table[table["code"] == code].sort_values("mois")
    return ville if len(ville) == 12 else None


def indicateurs_climat(code: str) -> dict:
    mois = climat_mensuel(code)
    if mois is None:
        return {}
    return {
        "temp_moy_annuelle": float(mois["temp_moy"].mean()),
        "precip_annuelles": float(mois["precip_mm"].sum()),
        "ensoleillement_annuel": float(mois["soleil_h"].sum()),
    }
