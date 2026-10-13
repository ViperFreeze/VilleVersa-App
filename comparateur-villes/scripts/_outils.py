"""Outils communs aux scripts de préparation des données."""
import sys
from pathlib import Path

import httpx
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_SOURCES = RACINE / "data" / "sources"  # fichiers bruts téléchargés (non versionnés)
DOSSIER_INDICATEURS = RACINE / "data" / "indicateurs"  # tables lues par l'appli


def telecharger(url: str, nom_fichier: str) -> Path:
    """Télécharge une fois dans data/sources/ ; réutilise le fichier ensuite."""
    DOSSIER_SOURCES.mkdir(parents=True, exist_ok=True)
    chemin = DOSSIER_SOURCES / nom_fichier
    if chemin.exists():
        print(f"  déjà présent : {chemin.name}")
        return chemin
    print(f"  téléchargement : {url}")
    with httpx.stream("GET", url, timeout=120, follow_redirects=True) as reponse:
        reponse.raise_for_status()
        with open(chemin, "wb") as f:
            for morceau in reponse.iter_bytes():
                f.write(morceau)
    return chemin


def verifier_colonnes(df: pd.DataFrame, attendues: list[str], fichier: str) -> None:
    """Arrête le script avec un message clair si le fichier n'a pas la forme prévue."""
    manquantes = [c for c in attendues if c not in df.columns]
    if manquantes:
        sys.exit(
            f"{fichier} : colonnes attendues absentes {manquantes}.\n"
            f"Colonnes trouvées : {list(df.columns)}\n"
            "Adaptez les noms de colonnes en haut du script."
        )


def enregistrer_indicateurs(df: pd.DataFrame, nom: str) -> None:
    """Écrit data/indicateurs/<nom>.csv : une colonne `code` + une colonne par indicateur."""
    DOSSIER_INDICATEURS.mkdir(parents=True, exist_ok=True)
    chemin = DOSSIER_INDICATEURS / f"{nom}.csv"
    df.to_csv(chemin, index=False)
    print(f"  écrit : {chemin.relative_to(RACINE)} ({len(df)} communes, colonnes {list(df.columns[1:])})")
