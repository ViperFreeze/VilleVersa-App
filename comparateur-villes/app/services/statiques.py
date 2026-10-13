"""Indicateurs issus des fichiers statiques (Insee, ANIL, DVF, MESR, BPE, SNCF).

Les scripts du dossier scripts/ transforment chaque fichier source en une
table simple, data/indicateurs/<source>.csv, avec :
- une colonne `code` (code INSEE de la commune),
- une colonne par indicateur, nommée comme dans app/config/profils.py.

Ce module lit toutes ces tables et les fusionne. Brancher une nouvelle
source revient donc à écrire son script de préparation, sans toucher à l'appli.
"""
import pandas as pd

from app.config.profils import INDICATEURS

from .outils import DOSSIER_DATA, cache_ttl, log

DOSSIER_INDICATEURS = DOSSIER_DATA / "indicateurs"


@cache_ttl(24 * 3600)
def _table() -> pd.DataFrame | None:
    fichiers = sorted(DOSSIER_INDICATEURS.glob("*.csv"))
    tables = []
    for fichier in fichiers:
        df = pd.read_csv(fichier, dtype={"code": str}).set_index("code")
        inconnues = [c for c in df.columns if c not in INDICATEURS]
        if inconnues:
            log.warning("%s : colonnes ignorées (absentes du catalogue) %s", fichier.name, inconnues)
        tables.append(df[[c for c in df.columns if c in INDICATEURS]])
    if not tables:
        return None
    return pd.concat(tables, axis=1)


def indicateurs(code: str) -> dict:
    table = _table()
    if table is None or code not in table.index:
        return {}
    ligne = table.loc[code]
    # .item() convertit les types numpy en types Python (sérialisables en JSON).
    return {cle: valeur.item() if hasattr(valeur, "item") else valeur
            for cle, valeur in ligne.items() if pd.notna(valeur)}
