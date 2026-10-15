"""Vérifie les trois API France Travail avec vos identifiants, pour un département.

Lancement :  python -m scripts.explorer_france_travail        (département 44)
             python -m scripts.explorer_france_travail 69     (autre département)

Affiche, sans jamais afficher les identifiants ni les jetons :
1. si chaque API délivre un jeton (abonnement et scopes corrects) ;
2. les combinaisons de critères acceptées par chaque indicateur pour un
   département (référentiel « details-indicateurs ») ;
3. la valeur que l'appli obtient avec les critères de app/services/francetravail.py ;
4. les équipements renvoyés par l'API Cadre de vie pour une commune.
Copiez la sortie complète si une valeur manque : elle dit quel critère changer.
"""
import logging
import sys

from app.main import charger_env
from app.services import francetravail as ft

INDICATEURS_A_VERIFIER = {  # id interne -> code indicateur France Travail
    "offres_12_mois_dep": "OFF_1",
    "demandeurs_a_dep": "DE_1",
    "salaries_dep": "SAL_1",
    "dynamisme_emploi_dep": "DYN_1",
}


def croisements(api: str, code_indicateur: str) -> None:
    retour = ft.appeler(api, "referentiel/details-indicateurs", params={"codeIndicateur": code_indicateur})
    details = (retour or {}).get("listeIndicateurs") or []
    if not details:
        print(f"    référentiel indisponible pour {code_indicateur}")
        return
    detail = details[0]
    types = [t.get("codeTypeTerritoire") for t in detail.get("listeTypesTerritoiresIndicateur") or []]
    print(f"    {code_indicateur} « {detail.get('libelleIndicateur')} » ; territoires : {types}")
    vus = sorted({
        (c.get("codeTypeActivite"), c.get("codeTypePeriode"), c.get("codeTypeNomenclature"), c.get("codeNomenclature"))
        for c in detail.get("listeCroisementsIndicateur") or []
        if c.get("codeTypeTerritoire") == "DEP"
    }, key=str)
    print(f"    croisements pour DEP (activité, période, type nomenclature, nomenclature) : {len(vus)}")
    for croisement in vus[:25]:
        print(f"      {croisement}")
    if len(vus) > 25:
        print(f"      ... et {len(vus) - 25} autres")


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="  %(levelname)s %(message)s")
    charger_env()
    dep = sys.argv[1] if len(sys.argv) > 1 else "44"
    if not ft.identifiants_presents():
        sys.exit("FT_CLIENT_ID et FT_CLIENT_SECRET absents : créez le fichier .env (voir .env.example).")

    print("1. Jetons")
    obtenus = 0
    for api in ft.API:
        ok = ft.jeton(api) is not None
        obtenus += ok
        print(f"  {api:10} {'OK' if ok else 'ÉCHEC (abonnement à cette API ou scope ?)'}")
    if not obtenus:
        sys.exit("Aucun jeton : vérifiez les identifiants du .env, l'abonnement aux API et la connexion.")

    print(f"\n2. Critères acceptés (département {dep})")
    for iid, code in INDICATEURS_A_VERIFIER.items():
        croisements(ft.REQUETES[iid][0], code)

    print(f"\n3. Valeurs obtenues par l'appli pour le département {dep}")
    for iid, (api, ressource, criteres, nomenclature) in ft.REQUETES.items():
        retour = ft.appeler(api, f"indicateur/{ressource}", corps={**ft.critere_territoire(dep), **criteres})
        lignes = (retour or {}).get("listeValeursParPeriode") or []
        nomenclatures = sorted({str(l.get("codeNomenclature")) for l in lignes})
        periodes = sorted({str(l.get("codePeriode")) for l in lignes})
        print(f"  {iid:22} valeur = {ft.derniere_valeur(retour, nomenclature)!r:12} "
              f"({len(lignes)} lignes, périodes {periodes[-2:]}, nomenclatures {nomenclatures[:8]})")

    print(f"\n4. Cadre de vie, département {dep}")
    communes = ft.cadre_vie_departement(dep)
    if not communes:
        print("  aucune commune reçue")
    else:
        code, equipements = max(communes.items(), key=lambda kv: sum(kv[1].values()))
        print(f"  {len(communes)} communes ; la mieux équipée : {code} -> {equipements}")


if __name__ == "__main__":
    main()
