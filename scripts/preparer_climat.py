"""Crée data/climat_mensuel.csv : moyennes mensuelles par ville (Open-Meteo, historique).

Pour chaque ville : données quotidiennes sur ANNEE_DEBUT-ANNEE_FIN, puis
- temp_moy  : moyenne des températures moyennes journalières du mois,
- precip_mm : cumul de pluie du mois, moyenné sur les années,
- soleil_h  : durée d'ensoleillement du mois en heures, moyennée sur les années.

Quotas de l'offre gratuite d'Open-Meteo : 600 appels par minute, 5 000 par
heure, 10 000 par jour. Une requête longue compte pour plusieurs appels :
poids = (jours / 14) x (variables / 10). Avec 5 ans et 3 variables, une ville
pèse environ 39 appels. Le script :
- regroupe les villes d'une même maille de 0,1° (~10 km, la résolution des
  données ERA5-Land) : une seule requête pour toute la maille ;
- espace les requêtes pour rester sous le quota horaire ;
- s'arrête avant le quota journalier, ou à la première erreur 429 ;
- reprend là où il s'était arrêté au lancement suivant (villes déjà présentes
  dans le fichier ignorées). Il faut donc peut-être le lancer deux jours de suite.

Choix à justifier dans le rapport : une normale climatique se calcule sur
30 ans ; 5 ans est un compromis imposé par les quotas de l'API gratuite.

Lancement :  python -m scripts.preparer_climat            (toutes les villes)
             python -m scripts.preparer_climat --limite 3  (essai sur 3 mailles)
"""
import argparse
import logging
import time
from datetime import date

import httpx
import pandas as pd

from app.services import geo, meteo
from app.services.outils import USER_AGENT

API_HISTORIQUE = "https://archive-api.open-meteo.com/v1/archive"
ANNEE_DEBUT, ANNEE_FIN = 2021, 2025
VARIABLES = ["temperature_2m_mean", "precipitation_sum", "sunshine_duration"]

# Quotas Open-Meteo, avec une marge.
QUOTA_HEURE = 4_500
QUOTA_JOUR = 9_000

NB_JOURS = (date(ANNEE_FIN, 12, 31) - date(ANNEE_DEBUT, 1, 1)).days + 1
POIDS_REQUETE = max(1.0, NB_JOURS / 14 * len(VARIABLES) / 10)
PAUSE_SECONDES = 3600 * POIDS_REQUETE / QUOTA_HEURE  # ~31 s


class QuotaAtteint(Exception):
    pass


def maille(ville: geo.Ville) -> tuple[float, float]:
    return round(ville.lat, 1), round(ville.lon, 1)


def climat_point(lat: float, lon: float) -> pd.DataFrame | None:
    """Moyennes mensuelles (mois, temp_moy, precip_mm, soleil_h) pour un point."""
    try:
        reponse = httpx.get(API_HISTORIQUE, params={
            "latitude": lat,
            "longitude": lon,
            "start_date": f"{ANNEE_DEBUT}-01-01",
            "end_date": f"{ANNEE_FIN}-12-31",
            "daily": ",".join(VARIABLES),
            "timezone": "auto",
        }, headers={"User-Agent": USER_AGENT}, timeout=60)
    except httpx.HTTPError as exc:
        logging.warning("Appel échoué (%s, %s) : %s %s", lat, lon, type(exc).__name__, exc)
        return None
    if reponse.status_code == 429:
        raise QuotaAtteint(reponse.text[:200])
    if reponse.status_code != 200:
        logging.warning("HTTP %s pour (%s, %s) : %s", reponse.status_code, lat, lon, reponse.text[:200])
        return None

    jours = pd.DataFrame(reponse.json()["daily"])
    jours["time"] = pd.to_datetime(jours["time"])
    jours["annee"], jours["mois"] = jours["time"].dt.year, jours["time"].dt.month
    par_mois_annee = jours.groupby(["annee", "mois"]).agg(
        temp_moy=("temperature_2m_mean", "mean"),
        precip_mm=("precipitation_sum", "sum"),
        soleil_h=("sunshine_duration", lambda s: s.sum() / 3600),  # secondes -> heures
    )
    return par_mois_annee.groupby("mois").mean().round(1).reset_index()


def charger_existant() -> pd.DataFrame | None:
    if not meteo.FICHIER_CLIMAT.exists():
        return None
    return pd.read_csv(meteo.FICHIER_CLIMAT, dtype={"code": str})


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="  %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--limite", type=int, help="ne traiter que les N premières mailles")
    args = parser.parse_args()

    villes = list((geo.liste_villes() or {}).values())
    if not villes:
        raise SystemExit("Liste des villes vide : lancez d'abord python -m scripts.preparer_villes")

    existant = charger_existant()
    deja_faits = set(existant["code"]) if existant is not None else set()

    mailles: dict[tuple, list[geo.Ville]] = {}
    for v in villes:
        if v.code not in deja_faits:
            mailles.setdefault(maille(v), []).append(v)
    a_faire = list(mailles.items())[: args.limite]
    max_ce_jour = int(QUOTA_JOUR // POIDS_REQUETE)

    print(f"{len(deja_faits)} villes déjà faites, {sum(len(vs) for _, vs in a_faire)} à faire "
          f"en {len(a_faire)} requêtes (poids ~{POIDS_REQUETE:.0f} chacune).")
    print(f"Une requête toutes les {PAUSE_SECONDES:.0f} s, {max_ce_jour} requêtes maximum aujourd'hui.")

    resultats, echecs = [], []
    try:
        for n, (_, vs) in enumerate(a_faire, 1):
            if n > max_ce_jour:
                print("Quota journalier atteint : relancez le script demain pour finir.")
                break
            noms = ", ".join(v.libelle for v in vs)
            print(f"[{n}/{len(a_faire)}] {noms}")
            mensuel = climat_point(vs[0].lat, vs[0].lon)
            if mensuel is None:
                echecs.extend(v.libelle for v in vs)
            else:
                for v in vs:
                    resultats.append(mensuel.assign(code=v.code)[["code", *mensuel.columns]])
            if n < len(a_faire):
                time.sleep(PAUSE_SECONDES)
    except QuotaAtteint as exc:
        print(f"Open-Meteo refuse (429, quota dépassé) : {exc}\n"
              "Ce qui est déjà fait est enregistré ; relancez le script plus tard.")
    except KeyboardInterrupt:
        print("\nInterrompu : ce qui est déjà fait est enregistré.")

    if resultats:
        tables = ([existant] if existant is not None else []) + resultats
        pd.concat(tables).to_csv(meteo.FICHIER_CLIMAT, index=False)
        print(f"Écrit : {meteo.FICHIER_CLIMAT} ({len(deja_faits) + len(resultats)} villes au total)")
    if echecs:
        print(f"Échecs ({len(echecs)}), repris au prochain lancement : {', '.join(echecs)}")


if __name__ == "__main__":
    main()
