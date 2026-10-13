"""Liste des villes de plus de 20 000 habitants et fiche d'identité (API Géo).

Source : https://geo.api.gouv.fr (DINUM), sans clé, 50 appels/s par IP.
La liste est lue dans data/villes.csv (créé par scripts/preparer_villes.py) ;
à défaut, elle est demandée à l'API au premier affichage.
"""
import unicodedata
from dataclasses import asdict, dataclass

import pandas as pd

from .outils import DOSSIER_DATA, cache_ttl, get_json, log

API_COMMUNES = "https://geo.api.gouv.fr/communes"
CHAMPS = "nom,code,population,surface,centre,departement,region"
SEUIL_POPULATION = 20_000
FICHIER_VILLES = DOSSIER_DATA / "villes.csv"


@dataclass(frozen=True)
class Ville:
    code: str  # code INSEE de la commune : la clé commune à toutes les sources
    nom: str
    population: int
    surface_ha: float
    lat: float
    lon: float
    code_departement: str
    departement: str
    region: str

    @property
    def libelle(self) -> str:
        """Ce que l'utilisateur voit et tape : « Nantes (44) »."""
        return f"{self.nom} ({self.code_departement})"

    @property
    def surface_km2(self) -> float:
        return self.surface_ha / 100

    @property
    def densite(self) -> float | None:
        return self.population / self.surface_km2 if self.surface_ha else None


def depuis_api(commune: dict) -> Ville:
    """Convertit une commune renvoyée par l'API Géo en Ville."""
    lon, lat = commune["centre"]["coordinates"]  # GeoJSON : longitude d'abord
    return Ville(
        code=commune["code"],
        nom=commune["nom"],
        population=int(commune.get("population") or 0),
        surface_ha=float(commune.get("surface") or 0),
        lat=lat,
        lon=lon,
        code_departement=commune["departement"]["code"],
        departement=commune["departement"]["nom"],
        region=commune["region"]["nom"],
    )


def telecharger_villes() -> list[Ville]:
    """Toutes les communes de plus de 20 000 habitants, depuis l'API Géo."""
    communes = get_json(API_COMMUNES, params={"fields": CHAMPS, "format": "json"})
    if not communes:
        return []
    villes = [
        depuis_api(c)
        for c in communes
        if (c.get("population") or 0) >= SEUIL_POPULATION and c.get("centre")
    ]
    return sorted(villes, key=lambda v: cle_tri(v.nom))


def cle_tri(texte: str) -> str:
    """Minuscules sans accents, pour trier et chercher (« Évry » avec les E)."""
    sans_accents = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return sans_accents.lower().strip()


@cache_ttl(24 * 3600)
def liste_villes() -> dict[str, Ville]:
    """Villes indexées par code INSEE, triées par nom."""
    if FICHIER_VILLES.exists():
        df = pd.read_csv(FICHIER_VILLES, dtype={"code": str, "code_departement": str})
        villes = [Ville(**ligne) for ligne in df.to_dict("records")]
    else:
        log.info("data/villes.csv absent : liste demandée à l'API Géo")
        villes = telecharger_villes()
    return {v.code: v for v in villes} or None  # None = rien trouvé, non mis en cache


def enregistrer_villes(villes: list[Ville]) -> None:
    pd.DataFrame([asdict(v) for v in villes]).to_csv(FICHIER_VILLES, index=False)


def trouver_ville(saisie: str) -> Ville | None:
    """Retrouve une ville à partir d'un code INSEE, d'un libellé ou d'un nom unique."""
    villes = liste_villes() or {}
    saisie = (saisie or "").strip()
    if saisie in villes:
        return villes[saisie]
    cle = cle_tri(saisie)
    par_libelle = [v for v in villes.values() if cle_tri(v.libelle) == cle]
    if par_libelle:
        return par_libelle[0]
    par_nom = [v for v in villes.values() if cle_tri(v.nom) == cle]
    return par_nom[0] if len(par_nom) == 1 else None  # homonymes : il faut le département
