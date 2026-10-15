"""Crée data/climat_mensuel.csv : moyennes mensuelles par ville (Open-Meteo, historique).

Pour chaque ville : données quotidiennes sur ANNEE_DEBUT-ANNEE_FIN, puis
- temp_moy  : moyenne des températures moyennes journalières du mois,
- precip_mm : cumul de pluie du mois, moyenné sur les années,
- soleil_h  : durée d'ensoleillement du mois en heures, moyennée sur les années.

Choix à justifier dans le rapport : une normale climatique se calcule
habituellement sur 30 ans ; 10 ans limite le volume demandé à l'API gratuite
(moins de 10 000 appels par jour, et un appel couvrant beaucoup de données
peut compter pour plusieurs).

Lancement :  python -m scripts.preparer_climat            (toutes les villes, ~10 min)
             python -m scripts.preparer_climat --limite 3  (essai sur 3 villes)
"""
import argparse
import logging
import time

import pandas as pd

from app.services import geo, meteo
from app.services.outils import get_json

API_HISTORIQUE = "https://archive-api.open-meteo.com/v1/archive"
ANNEE_DEBUT, ANNEE_FIN = 2016, 2025
PAUSE_SECONDES = 1.0


def climat_ville(ville: geo.Ville) -> pd.DataFrame | None:
    data = get_json(API_HISTORIQUE, params={
        "latitude": ville.lat,
        "longitude": ville.lon,
        "start_date": f"{ANNEE_DEBUT}-01-01",
        "end_date": f"{ANNEE_FIN}-12-31",
        "daily": "temperature_2m_mean,precipitation_sum,sunshine_duration",
        "timezone": "auto",
    }, timeout=60)  # 10 ans de données : réponse lente
    if not data or "daily" not in data:
        return None
    jours = pd.DataFrame(data["daily"])
    jours["time"] = pd.to_datetime(jours["time"])
    jours["annee"], jours["mois"] = jours["time"].dt.year, jours["time"].dt.month
    par_mois_annee = jours.groupby(["annee", "mois"]).agg(
        temp_moy=("temperature_2m_mean", "mean"),
        precip_mm=("precipitation_sum", "sum"),
        soleil_h=("sunshine_duration", lambda s: s.sum() / 3600),  # secondes -> heures
    )
    mensuel = par_mois_annee.groupby("mois").mean().round(1).reset_index()
    mensuel.insert(0, "code", ville.code)
    return mensuel


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="  %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--limite", type=int, help="ne traiter que les N premières villes")
    args = parser.parse_args()

    villes = list((geo.liste_villes() or {}).values())[: args.limite]
    resultats, echecs = [], []
    for n, ville in enumerate(villes, 1):
        print(f"[{n}/{len(villes)}] {ville.libelle}")
        mensuel = climat_ville(ville)
        if mensuel is not None:
            resultats.append(mensuel)
        else:
            echecs.append(ville.libelle)
        time.sleep(PAUSE_SECONDES)

    if resultats:
        pd.concat(resultats).to_csv(meteo.FICHIER_CLIMAT, index=False)
        print(f"Écrit : {meteo.FICHIER_CLIMAT} ({len(resultats)} villes)")
    if echecs:
        print(f"Échecs ({len(echecs)}), à relancer : {', '.join(echecs)}")


if __name__ == "__main__":
    main()
