"""Emploi et équipements : trois API de France Travail (francetravail.io).

- Marché du travail : offres déposées et demandeurs d'emploi.
- Informations sur un territoire : salariés et indicateur de dynamisme de l'emploi.
- Cadre de vie des communes (eTerritoire) : nombre d'équipements par commune.

Les deux API statistiques ne descendent pas à la commune (Data Emploi n'a
pas de données communales) : leurs indicateurs sont donnés pour le
DÉPARTEMENT de la ville, ce que leurs libellés précisent. Le cadre de vie,
lui, est communal.

Accès : une application sur francetravail.io abonnée aux trois API ; les
identifiants sont lus dans FT_CLIENT_ID et FT_CLIENT_SECRET (fichier .env en
local, variables d'environnement sur Render). Un jeton OAuth2 est demandé
par API, avec les scopes indiqués dans sa documentation (fichiers OpenAPI).
Limite : 10 appels par seconde. Sans identifiants, les indicateurs
s'affichent « — ».

Les codes d'activité (CUMUL, MOYENNE) et de nomenclature ci-dessous sont
ceux des exemples de la documentation : `python -m scripts.explorer_france_travail`
vérifie qu'ils renvoient bien des valeurs.
"""
import os
import time

import httpx

from .geo import Ville, cle_tri
from .outils import TIMEOUT, USER_AGENT, cache_ttl, log

URL_JETON = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
URL_JETON_ETERRITOIRE = (
    "https://authentification-partenaire.francetravail.io/connexion/oauth2/access_token?realm=/partenaire"
)

# API -> (URL de base, URL du jeton, scopes)
API = {
    "marche": (
        "https://api.francetravail.io/partenaire/stats-offres-demandes-emploi/v1",
        URL_JETON,
        "api_stats-offres-demandes-emploiv1 offresetdemandesemploi",
    ),
    "territoire": (
        "https://api.francetravail.io/partenaire/stats-informations-territoire/v1",
        URL_JETON,
        "api_stats-informations-territoirev1 infosterritoire",
    ),
    "cadre_vie": (
        "https://api.francetravail.io/partenaire/eterritoire/v1",
        URL_JETON_ETERRITOIRE,
        "api_eterritoirev1",
    ),
}

# Requêtes statistiques : id interne -> (API, ressource, critères, nomenclature à lire)
REQUETES = {
    "offres_12_mois_dep": ("marche", "stat-offres", {
        "codeTypeActivite": "CUMUL", "codeActivite": "CUMUL",
        "codeTypePeriode": "TRIMESTRE", "codeTypeNomenclature": "ORIGINEOFF",
    }, "TOFF-CUMUL12MOIS"),
    "demandeurs_a_dep": ("marche", "stat-demandeurs", {
        "codeTypeActivite": "CUMUL", "codeActivite": "CUMUL",
        "codeTypePeriode": "TRIMESTRE", "codeTypeNomenclature": "CATCAND",
    }, "A"),
    "salaries_dep": ("territoire", "stat-salaries", {
        "codeTypeActivite": "CUMUL", "codeActivite": "CUMUL", "codeTypePeriode": "ANNEE",
    }, None),
    "dynamisme_emploi_dep": ("territoire", "stat-dynamique-emploi", {
        "codeTypeActivite": "MOYENNE", "codeActivite": "MOYENNE", "codeTypePeriode": "TRIMESTRE",
    }, None),
}

# Catégories d'équipements d'eTerritoire (clé sans accents) -> id d'indicateur.
EQUIPEMENTS = {
    "equipements sportifs": "equip_sport",
    "sante": "equip_sante",
    "education": "equip_education",
    "loisirs": "equip_loisirs",
    "services publics": "equip_services_publics",
}

# Ordre de lecture de la valeur principale d'une période.
CHAMPS_VALEUR = ("valeurPrincipaleNombre", "valeurPrincipaleDecimale", "valeurPrincipaleTaux",
                 "valeurPrincipaleMontant", "valeurPrincipaleRang")

_jetons: dict[str, tuple[str, float]] = {}


def identifiants_presents() -> bool:
    return bool(os.environ.get("FT_CLIENT_ID") and os.environ.get("FT_CLIENT_SECRET"))


def jeton(api: str) -> str | None:
    """Jeton OAuth2 (client credentials) de l'API, réutilisé jusqu'à son expiration."""
    trouve = _jetons.get(api)
    if trouve and time.monotonic() < trouve[1]:
        return trouve[0]
    _, url_jeton, scope = API[api]
    try:
        reponse = httpx.post(url_jeton, data={
            "grant_type": "client_credentials",
            "client_id": os.environ["FT_CLIENT_ID"],
            "client_secret": os.environ["FT_CLIENT_SECRET"],
            "scope": scope,
        }, timeout=TIMEOUT)
        reponse.raise_for_status()
        corps = reponse.json()
        valeur = corps["access_token"]
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        detail = getattr(getattr(exc, "response", None), "text", "")[:200]
        log.warning("Jeton France Travail (%s) non obtenu : %s %s", api, exc, detail)
        return None
    _jetons[api] = (valeur, time.monotonic() + corps.get("expires_in", 1500) - 60)
    return valeur


def appeler(api: str, chemin: str, *, corps: dict | None = None, params: dict | None = None):
    """POST (si `corps`) ou GET sur l'API ; JSON, ou None si l'appel échoue ou ne renvoie rien."""
    cle = jeton(api)
    if not cle:
        return None
    url = f"{API[api][0]}/{chemin}"
    entetes = {"Authorization": f"Bearer {cle}", "Accept": "application/json", "User-Agent": USER_AGENT}
    try:
        if corps is not None:
            reponse = httpx.post(url, json=corps, headers=entetes, timeout=TIMEOUT)
        else:
            reponse = httpx.get(url, params=params, headers=entetes, timeout=TIMEOUT)
        if reponse.status_code == 204:
            return None
        reponse.raise_for_status()
        return reponse.json()
    except (httpx.HTTPError, ValueError) as exc:
        detail = getattr(getattr(exc, "response", None), "text", "")[:200]
        log.warning("France Travail %s/%s : %s %s", api, chemin, exc, detail)
        return None


def derniere_valeur(retour: dict | None, nomenclature: str | None = None):
    """Valeur principale de la période la plus récente (filtrée sur une nomenclature)."""
    lignes = [
        ligne for ligne in (retour or {}).get("listeValeursParPeriode") or []
        if nomenclature is None or ligne.get("codeNomenclature") == nomenclature
    ]
    if not lignes:
        return None
    derniere = max(lignes, key=lambda ligne: ligne.get("codePeriode") or "")
    return next((derniere[c] for c in CHAMPS_VALEUR if derniere.get(c) is not None), None)


def critere_territoire(code_departement: str) -> dict:
    return {"codeTypeTerritoire": "DEP", "codeTerritoire": code_departement, "dernierePeriode": True}


@cache_ttl(24 * 3600)
def stats_departement(code_departement: str) -> dict | None:
    """Indicateurs statistiques du département (publiés chaque trimestre : cache 24 h)."""
    valeurs = {}
    for iid, (api, ressource, criteres, nomenclature) in REQUETES.items():
        retour = appeler(api, f"indicateur/{ressource}",
                         corps={**critere_territoire(code_departement), **criteres})
        valeur = derniere_valeur(retour, nomenclature)
        if valeur is not None:
            valeurs[iid] = valeur
    return valeurs or None  # None : rien obtenu, on réessaiera au prochain affichage


@cache_ttl(24 * 3600)
def cadre_vie_departement(code_departement: str) -> dict | None:
    """Équipements de chaque commune du département : {code Insee: {id indicateur: nombre}}."""
    dep = str(int(code_departement)) if code_departement.isdigit() else code_departement
    communes = appeler("cadre_vie", "cadre-de-vie.php", params={"dep": dep})
    if not isinstance(communes, list):
        return None
    resultat = {}
    for commune in communes:
        equipements = commune.get("equipements") or {}
        resultat[str(commune.get("idinsee"))] = {
            EQUIPEMENTS[cle_tri(nom)]: nombre
            for nom, nombre in equipements.items()
            if cle_tri(nom) in EQUIPEMENTS and nombre is not None
        }
    return resultat


def indicateurs(ville: Ville) -> dict:
    """Tous les indicateurs France Travail d'une ville ; {} sans identifiants."""
    if not identifiants_presents():
        return {}
    valeurs = dict(stats_departement(ville.code_departement) or {})
    offres, demandeurs = valeurs.get("offres_12_mois_dep"), valeurs.get("demandeurs_a_dep")
    if offres is not None and demandeurs:
        valeurs["offres_pour_100_demandeurs"] = offres / demandeurs * 100
    valeurs |= (cadre_vie_departement(ville.code_departement) or {}).get(ville.code, {})
    return valeurs
