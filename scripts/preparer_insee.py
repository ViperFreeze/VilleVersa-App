"""Crée data/indicateurs/insee.csv depuis la base du comparateur de territoires (Insee).

Source : https://www.insee.fr/fr/statistiques/2521169 (Licence Ouverte 2.0,
mention « Source : Insee »). Le fichier est au format long : une ligne par
territoire, indicateur (TAB_MEASURE) et période (TIME_PERIOD).

Deux étapes :
1. python -m scripts.preparer_insee --explorer
   écrit data/sources/insee_mesures.csv : la liste des niveaux géographiques,
   des indicateurs disponibles et de leurs périodes. Choisissez-y les codes.
2. Renseignez MESURES ci-dessous, puis :  python -m scripts.preparer_insee

Paris, Lyon et Marseille figurent en commune entière et par arrondissement :
le filtre sur le niveau « commune » garde la commune entière.
"""
import argparse
import sys

import pandas as pd

from scripts._outils import DOSSIER_SOURCES, enregistrer_indicateurs, telecharger

URL_PARQUET = "https://www.insee.fr/fr/statistiques/fichier/2521169/comparateur.parquet"

# id d'indicateur (app/config/profils.py)  ->  code TAB_MEASURE de l'Insee.
# À REMPLIR après l'étape --explorer, par exemple : "taux_chomage": "<code lu dans insee_mesures.csv>"
MESURES: dict[str, str] = {}

# Valeur de GEO_OBJECT qui désigne les communes : à confirmer avec --explorer.
NIVEAU_COMMUNE = "COM"


def charger() -> pd.DataFrame:
    chemin = telecharger(URL_PARQUET, "insee_comparateur.parquet")
    return pd.read_parquet(chemin)  # nécessite pyarrow


def explorer(df: pd.DataFrame) -> None:
    resume = (
        df.groupby(["GEO_OBJECT", "GEO_OBJECT_LABEL", "TAB_MEASURE", "TAB_MEASURE_LABEL", "TIME_PERIOD"])
        .size().rename("nb_lignes").reset_index()
    )
    chemin = DOSSIER_SOURCES / "insee_mesures.csv"
    resume.to_csv(chemin, index=False)
    print(f"Écrit : {chemin}")
    print("Niveaux géographiques :", sorted(df["GEO_OBJECT"].unique()))


def preparer(df: pd.DataFrame) -> None:
    if not MESURES:
        sys.exit("MESURES est vide : lancez d'abord --explorer, puis renseignez les codes dans ce script.")
    communes = df[(df["GEO_OBJECT"] == NIVEAU_COMMUNE) & df["TAB_MEASURE"].isin(MESURES.values())]
    # Pour chaque indicateur, on garde la période la plus récente.
    communes = communes.sort_values("TIME_PERIOD").groupby(["GEO", "TAB_MEASURE"]).tail(1)
    table = communes.pivot(index="GEO", columns="TAB_MEASURE", values="OBS_VALUE")
    table = table.rename(columns={code: iid for iid, code in MESURES.items()})
    table.index.name = "code"
    enregistrer_indicateurs(table.reset_index(), "insee")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--explorer", action="store_true", help="lister les indicateurs disponibles")
    args = parser.parse_args()
    df = charger()
    if args.explorer:
        explorer(df)
    else:
        preparer(df)


if __name__ == "__main__":
    main()
