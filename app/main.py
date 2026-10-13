"""Application FastAPI : pages HTML et API JSON du comparateur de villes.

Lancement en local :  uvicorn app.main:app --reload
"""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import graphiques
from app.config.profils import (INDICATEURS, PROFIL_PAR_DEFAUT, PROFILS, THEMES,
                                indicateurs_du_theme)
from app.services import fiche, geo

DOSSIER_APP = Path(__file__).resolve().parent


def charger_env(chemin: Path = DOSSIER_APP.parent / ".env") -> None:
    """Lit le fichier .env local (identifiants France Travail), s'il existe."""
    if not chemin.exists():
        return
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if "=" in ligne and not ligne.lstrip().startswith("#"):
            cle, valeur = ligne.split("=", 1)
            os.environ.setdefault(cle.strip(), valeur.strip())


charger_env()

app = FastAPI(title="Comparateur de villes françaises")
app.mount("/static", StaticFiles(directory=DOSSIER_APP / "static"), name="static")
templates = Jinja2Templates(directory=DOSSIER_APP / "templates")


def formater(valeur, indicateur) -> str:
    """Valeur à la française : 327 734 hab., 12,4 €/m²."""
    if valeur is None:
        return "—"
    if isinstance(valeur, str):
        return valeur
    texte = indicateur.format.format(valeur)
    texte = texte.replace(",", " ").replace(".", ",")  # espace fine, virgule décimale
    return f"{texte} {indicateur.unite}".strip()


templates.env.filters["formater"] = formater


# ---------------------------------------------------------------- pages HTML

def _page_accueil(request: Request, erreur: str | None = None, saisie: dict | None = None,
                  statut: int = 200):
    villes = geo.liste_villes() or {}
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "villes": list(villes.values()),
            "profils": list(PROFILS.values()),
            "erreur": erreur,
            "saisie": saisie or {"profil": PROFIL_PAR_DEFAUT, "a": "", "b": ""},
        },
        status_code=statut,
    )


@app.get("/", response_class=HTMLResponse)
def accueil(request: Request):
    return _page_accueil(request)


@app.get("/comparer", response_class=HTMLResponse)
def comparer(request: Request, a: str = "", b: str = "", profil: str = PROFIL_PAR_DEFAUT):
    saisie = {"profil": profil, "a": a, "b": b}
    p = PROFILS.get(profil)
    ville_a, ville_b = geo.trouver_ville(a), geo.trouver_ville(b)

    erreurs = []
    if p is None:
        erreurs.append("Profil inconnu.")
    if ville_a is None:
        erreurs.append(f"Ville A introuvable : « {a} ». Choisissez-la dans la liste.")
    if ville_b is None:
        erreurs.append(f"Ville B introuvable : « {b} ». Choisissez-la dans la liste.")
    if ville_a and ville_b and ville_a.code == ville_b.code:
        erreurs.append("Choisissez deux villes différentes.")
    if erreurs:
        return _page_accueil(request, " ".join(erreurs), saisie, statut=422)

    fiches = [fiche.construire(ville_a), fiche.construire(ville_b)]
    onglets = [
        {"id": t, "titre": THEMES[t], "indicateurs": indicateurs_du_theme(p, t)}
        for t in p.themes
    ]
    return templates.TemplateResponse(
        request,
        "comparer.html",
        {
            "profil": p,
            "fiches": fiches,
            "onglets": onglets,
            "saisie": saisie,
            "graphique_previsions": graphiques.previsions(fiches),
            "graphique_climat": graphiques.climat(fiches),
        },
    )


# ---------------------------------------------------------------- API JSON

@app.get("/api/villes")
def api_villes(q: str = ""):
    """Villes de plus de 20 000 habitants ; `q` filtre sur le début du nom."""
    cle = geo.cle_tri(q)
    villes = (geo.liste_villes() or {}).values()
    return [
        {"code": v.code, "nom": v.nom, "libelle": v.libelle, "population": v.population}
        for v in villes
        if geo.cle_tri(v.nom).startswith(cle)
    ]


@app.get("/api/ville/{code}")
def api_ville(code: str):
    """Toutes les valeurs d'indicateurs d'une ville (utile pour tester les sources)."""
    ville = (geo.liste_villes() or {}).get(code)
    if ville is None:
        raise HTTPException(status_code=404, detail="Ville inconnue ou sous 20 000 habitants")
    f = fiche.construire(ville)
    return {
        "code": ville.code,
        "nom": ville.nom,
        "indicateurs": {
            cle: {"valeur": valeur, "libelle": INDICATEURS[cle].libelle,
                  "unite": INDICATEURS[cle].unite, "source": INDICATEURS[cle].source}
            for cle, valeur in f.valeurs.items()
        },
        "resume": f.resume,
        "previsions": f.previsions,
    }
