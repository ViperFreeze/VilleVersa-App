"""Résumé et image de la ville (API REST de Wikipédia en français).

Texte sous licence CC BY-SA 4.0 : le lien vers l'article est affiché avec le résumé.
"""
from urllib.parse import quote

from .outils import cache_ttl, get_json

API_RESUME = "https://fr.wikipedia.org/api/rest_v1/page/summary/{titre}"


@cache_ttl(24 * 3600)
def resume(nom: str, departement: str) -> dict | None:
    """Résumé de l'article ; essaie « Nom (Département) » si le nom est ambigu."""
    for titre in (nom, f"{nom} ({departement})"):
        data = get_json(API_RESUME.format(titre=quote(titre.replace(" ", "_"))))
        # TODO à vérifier au premier test : une page d'homonymie a type == "disambiguation".
        if data and data.get("type") == "standard":
            return {
                "titre": data.get("title"),
                "extrait": data.get("extract"),
                "image": (data.get("thumbnail") or {}).get("source"),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
            }
    return None
