"""Outils partagés par les services : appels HTTP et cache en mémoire."""
import functools
import logging
import time
from pathlib import Path

import httpx

log = logging.getLogger("comparateur")

DOSSIER_DATA = Path(__file__).resolve().parents[2] / "data"
USER_AGENT = "ComparateurVilles/0.1 (projet etudiant BUT Informatique)"
TIMEOUT = httpx.Timeout(10.0)


def get_json(url: str, params: dict | None = None, headers: dict | None = None):
    """GET qui renvoie le JSON, ou None si l'appel échoue (l'appli ne plante pas)."""
    entetes = {"User-Agent": USER_AGENT, **(headers or {})}
    try:
        reponse = httpx.get(url, params=params, headers=entetes, timeout=TIMEOUT)
        reponse.raise_for_status()
        return reponse.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("Appel échoué %s : %s", url, exc)
        return None


def cache_ttl(secondes: int):
    """Garde le résultat d'une fonction en mémoire pendant `secondes`.

    Les résultats None (appel échoué) ne sont pas gardés, pour réessayer au
    prochain affichage.
    """
    def decorateur(fonction):
        memoire: dict = {}

        @functools.wraps(fonction)
        def enveloppe(*args):
            maintenant = time.monotonic()
            trouve = memoire.get(args)
            if trouve and maintenant - trouve[0] < secondes:
                return trouve[1]
            valeur = fonction(*args)
            if valeur is not None:
                memoire[args] = (maintenant, valeur)
            return valeur

        enveloppe.vider_cache = memoire.clear
        return enveloppe

    return decorateur
