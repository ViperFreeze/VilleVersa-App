"""Assemble, pour une ville, toutes les données affichées dans la comparaison."""
from dataclasses import dataclass, field

from . import emploi, meteo, statiques, wikipedia
from .geo import Ville


@dataclass
class Fiche:
    ville: Ville
    valeurs: dict = field(default_factory=dict)  # id d'indicateur -> valeur
    resume: dict | None = None  # Wikipédia
    previsions: dict | None = None  # Open-Meteo, prochains jours
    climat: object = None  # DataFrame des moyennes mensuelles, ou None


def construire(ville: Ville) -> Fiche:
    valeurs = {
        "population": ville.population,
        "surface_km2": ville.surface_km2,
        "densite": ville.densite,
        "departement": f"{ville.departement} ({ville.code_departement})",
        "region": ville.region,
    }
    valeurs |= statiques.indicateurs(ville.code)
    valeurs |= meteo.indicateurs_climat(ville.code)
    valeurs |= emploi.indicateurs_emploi(ville.code)
    return Fiche(
        ville=ville,
        valeurs=valeurs,
        resume=wikipedia.resume(ville.nom, ville.departement),
        previsions=meteo.previsions(ville.lat, ville.lon),
        climat=meteo.climat_mensuel(ville.code),
    )
