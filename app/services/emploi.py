"""Offres d'emploi en cours (API Offres d'emploi v2 de France Travail).

Accès : inscription sur https://francetravail.io, puis création d'une
application abonnée à l'API « Offres d'emploi ». Les identifiants sont lus
dans les variables d'environnement FT_CLIENT_ID et FT_CLIENT_SECRET :
ne jamais les écrire dans le code ni les pousser sur GitHub.
Limite indiquée sur data.gouv.fr : 10 appels par seconde.

Sans identifiants, les indicateurs d'emploi s'affichent comme « non disponibles ».

TODO à vérifier sur la documentation de francetravail.io au moment de l'inscription :
- l'URL du jeton et le « scope » ci-dessous ;
- le nom des paramètres `commune` et `typeContrat` ;
- Paris, Lyon et Marseille : la recherche attend peut-être les codes d'arrondissement.
"""
import os
import time

import httpx

from .outils import TIMEOUT, USER_AGENT, cache_ttl, log

URL_JETON = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
URL_RECHERCHE = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
SCOPE = "api_offresdemploiv2 o2dsoffre"

_jeton = {"valeur": None, "expire": 0.0}


def identifiants_presents() -> bool:
    return bool(os.environ.get("FT_CLIENT_ID") and os.environ.get("FT_CLIENT_SECRET"))


def _obtenir_jeton() -> str | None:
    """Jeton OAuth2 (client credentials), réutilisé jusqu'à son expiration."""
    if _jeton["valeur"] and time.monotonic() < _jeton["expire"]:
        return _jeton["valeur"]
    try:
        reponse = httpx.post(
            URL_JETON,
            data={
                "grant_type": "client_credentials",
                "client_id": os.environ["FT_CLIENT_ID"],
                "client_secret": os.environ["FT_CLIENT_SECRET"],
                "scope": SCOPE,
            },
            timeout=TIMEOUT,
        )
        reponse.raise_for_status()
        corps = reponse.json()
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.warning("Jeton France Travail non obtenu : %s", exc)
        return None
    _jeton["valeur"] = corps["access_token"]
    _jeton["expire"] = time.monotonic() + corps.get("expires_in", 1500) - 60
    return _jeton["valeur"]


def _compter_offres(code_commune: str, **filtres) -> int | None:
    """Nombre total d'offres, lu dans l'en-tête Content-Range (« offres 0-0/1234 »)."""
    jeton = _obtenir_jeton()
    if not jeton:
        return None
    try:
        reponse = httpx.get(
            URL_RECHERCHE,
            params={"commune": code_commune, "range": "0-0", **filtres},
            headers={"Authorization": f"Bearer {jeton}", "User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        if reponse.status_code == 204:  # aucune offre
            return 0
        reponse.raise_for_status()
        return int(reponse.headers["Content-Range"].rsplit("/", 1)[1])
    except (httpx.HTTPError, KeyError, ValueError, IndexError) as exc:
        log.warning("Recherche France Travail échouée pour %s : %s", code_commune, exc)
        return None


@cache_ttl(3600)
def indicateurs_emploi(code_commune: str) -> dict:
    if not identifiants_presents():
        return {}
    resultats = {
        "nb_offres": _compter_offres(code_commune),
        "nb_offres_cdi": _compter_offres(code_commune, typeContrat="CDI"),
    }
    return {cle: valeur for cle, valeur in resultats.items() if valeur is not None}
