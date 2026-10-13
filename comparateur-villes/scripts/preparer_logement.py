"""Crée data/indicateurs/logement.csv : loyers (ANIL) et prix de vente (DVF) par commune.

Sources (Licence Ouverte 2.0) :
- Carte des loyers 2025, ANIL : loyers d'annonce au m², charges comprises, 3e trimestre 2025.
  Mention obligatoire : « Estimations ANIL, à partir des données du Groupe SeLoger et de leboncoin ».
- Statistiques DVF, data.gouv.fr : prix médian au m² sur les 10 derniers semestres.

Les noms de colonnes ci-dessous sont à confirmer au premier lancement :
le script s'arrête avec la liste des colonnes réelles s'ils ne correspondent pas.

Lancement :  python -m scripts.preparer_logement
"""
import pandas as pd

from scripts._outils import enregistrer_indicateurs, telecharger, verifier_colonnes

BASE_ANIL = "https://static.data.gouv.fr/resources/carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2025"
FICHIERS_ANIL = {
    "loyer_m2_appartement": f"{BASE_ANIL}/20251211-145010/pred-app-mef-dhup.csv",
    "loyer_m2_t1t2": f"{BASE_ANIL}/20251211-144934/pred-app12-mef-dhup.csv",
    "loyer_m2_t3plus": f"{BASE_ANIL}/20251211-144951/pred-app3-mef-dhup.csv",
    "loyer_m2_maison": f"{BASE_ANIL}/20251211-145039/pred-mai-mef-dhup.csv",
}
ANIL_CODE, ANIL_LOYER = "INSEE_C", "loypredm2"  # à confirmer

URL_DVF = "https://data-pipeline-open.s3.sbg.io.cloud.ovh.net/dvf/stats_whole_period.csv"
DVF_CODE, DVF_ECHELLE = "code_geo", "echelle_geo"  # à confirmer
DVF_PRIX = {
    "prix_m2_appartement": "med_prix_m2_whole_appartement",
    "prix_m2_maison": "med_prix_m2_whole_maison",
}


def lire_csv_anil(chemin) -> pd.DataFrame:
    for encodage in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(chemin, sep=";", decimal=",", encoding=encodage, dtype={ANIL_CODE: str})
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Encodage non reconnu : {chemin}")


def loyers() -> pd.DataFrame:
    colonnes = []
    for indicateur, url in FICHIERS_ANIL.items():
        chemin = telecharger(url, url.rsplit("/", 1)[1])
        df = lire_csv_anil(chemin)
        verifier_colonnes(df, [ANIL_CODE, ANIL_LOYER], chemin.name)
        colonnes.append(df.set_index(ANIL_CODE)[ANIL_LOYER].rename(indicateur))
    return pd.concat(colonnes, axis=1)


def prix_dvf() -> pd.DataFrame:
    chemin = telecharger(URL_DVF, "dvf_stats_whole_period.csv")
    df = pd.read_csv(chemin, dtype={DVF_CODE: str}, low_memory=False)
    verifier_colonnes(df, [DVF_CODE, DVF_ECHELLE, *DVF_PRIX.values()], chemin.name)
    communes = df[df[DVF_ECHELLE] == "commune"].set_index(DVF_CODE)
    return communes[list(DVF_PRIX.values())].rename(columns={v: k for k, v in DVF_PRIX.items()})


def main() -> None:
    print("Loyers ANIL")
    table_loyers = loyers()
    print("Prix DVF")
    table_prix = prix_dvf()
    table = table_loyers.join(table_prix, how="outer").round(1)
    table.index.name = "code"
    enregistrer_indicateurs(table.reset_index(), "logement")


if __name__ == "__main__":
    main()
