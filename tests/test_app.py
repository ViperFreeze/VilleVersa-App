"""Tests de l'appli, sans réseau : les appels aux API sont remplacés par des réponses types.

Lancement depuis la racine :  python -m pytest
"""
import pytest
from fastapi.testclient import TestClient

from app.config.profils import (INDICATEURS, PROFILS, THEMES, THEMES_OBLIGATOIRES,
                                indicateurs_du_theme)
from app.main import app
from app.services import emploi, geo, meteo, statiques, wikipedia

# Réponse réelle de l'API Géo pour Nantes (appel du 09/10/2026).
NANTES_API = {
    "nom": "Nantes", "code": "44109", "population": 327734, "surface": 6572.58,
    "centre": {"type": "Point", "coordinates": [-1.5603, 47.2382]},
    "codesPostaux": ["44000", "44100", "44200", "44300"],
    "departement": {"code": "44", "nom": "Loire-Atlantique"},
    "region": {"code": "52", "nom": "Pays de la Loire"},
}
RENNES = geo.Ville("35238", "Rennes", 225081, 5039.0, 48.11, -1.68, "35", "Ille-et-Vilaine", "Bretagne")
PREVISIONS = {"dates": ["2026-10-13", "2026-10-14"], "tmax": [17.2, 18.0],
              "tmin": [9.1, 10.4], "pluie_mm": [0.0, 2.3], "code_meteo": [3, 61]}


@pytest.fixture
def client(monkeypatch):
    nantes = geo.depuis_api(NANTES_API)
    villes = {nantes.code: nantes, RENNES.code: RENNES}
    monkeypatch.setattr(geo, "liste_villes", lambda: villes)
    monkeypatch.setattr(wikipedia, "resume", lambda nom, dep: None)
    monkeypatch.setattr(meteo, "previsions", lambda lat, lon: PREVISIONS)
    monkeypatch.setattr(meteo, "climat_mensuel", lambda code: None)
    monkeypatch.setattr(meteo, "indicateurs_climat", lambda code: {})
    monkeypatch.setattr(emploi, "indicateurs_emploi", lambda code: {})
    monkeypatch.setattr(statiques, "indicateurs",
                        lambda code: {"loyer_m2_t1t2": 14.83} if code == "44109" else {})
    return TestClient(app)


# ---------------------------------------------------------------- configuration

def test_chaque_profil_contient_les_themes_obligatoires():
    for profil in PROFILS.values():
        assert set(THEMES_OBLIGATOIRES) <= set(profil.themes), profil.id


def test_les_indicateurs_mis_en_avant_existent_et_sont_affiches():
    for profil in PROFILS.values():
        for iid in profil.mis_en_avant:
            assert iid in INDICATEURS, f"{profil.id} : {iid} absent du catalogue"
            assert INDICATEURS[iid].theme in profil.themes, f"{profil.id} : onglet de {iid} absent"


def test_chaque_indicateur_a_un_theme_connu():
    assert all(i.theme in THEMES for i in INDICATEURS.values())


def test_le_profil_change_l_ordre_des_indicateurs():
    logement_famille = indicateurs_du_theme(PROFILS["famille"], "logement")
    logement_etudiant = indicateurs_du_theme(PROFILS["etudiant"], "logement")
    assert logement_famille[0].id == "loyer_m2_t3plus"
    assert logement_etudiant[0].id == "loyer_m2_t1t2"


# ---------------------------------------------------------------- services

def test_conversion_api_geo():
    ville = geo.depuis_api(NANTES_API)
    assert (ville.lat, ville.lon) == (47.2382, -1.5603)  # GeoJSON : longitude en premier
    assert ville.libelle == "Nantes (44)"
    assert round(ville.surface_km2, 1) == 65.7
    assert round(ville.densite) == 4986


def test_telecharger_villes_par_departement(monkeypatch):
    petite = {**NANTES_API, "nom": "Petiteville", "code": "44999", "population": 900}
    reponses = {
        geo.API_DEPARTEMENTS: [{"code": "44"}],
        f"{geo.API_DEPARTEMENTS}/44/communes": [NANTES_API, petite],
    }
    monkeypatch.setattr(geo, "get_json", lambda url, **kw: reponses.get(url))
    assert [v.nom for v in geo.telecharger_villes()] == ["Nantes"]  # sous 20 000 hab. exclue

    # Un département en échec : pas de liste incomplète.
    reponses[geo.API_DEPARTEMENTS] = [{"code": "44"}, {"code": "35"}]
    assert geo.telecharger_villes() == []


def test_trouver_ville(client):
    assert geo.trouver_ville("Nantes (44)").code == "44109"
    assert geo.trouver_ville("nantes").code == "44109"
    assert geo.trouver_ville("44109").nom == "Nantes"
    assert geo.trouver_ville("Brest") is None


# ---------------------------------------------------------------- pages et API

def test_accueil_liste_les_villes(client):
    page = client.get("/")
    assert page.status_code == 200
    assert '<option value="Nantes (44)">' in page.text


def test_comparaison(client):
    page = client.get("/comparer", params={"profil": "etudiant", "a": "Nantes (44)", "b": "Rennes (35)"})
    assert page.status_code == 200
    assert "Formation" in page.text  # onglet propre au profil étudiant
    assert "327 734 hab." in page.text  # nombre formaté à la française
    assert "14,8 €/m²" in page.text
    assert "fig-previsions" in page.text


def test_ville_inconnue_renvoie_le_formulaire(client):
    page = client.get("/comparer", params={"a": "Nantes (44)", "b": "Atlantide"})
    assert page.status_code == 422
    assert "Atlantide" in page.text


def test_deux_fois_la_meme_ville(client):
    page = client.get("/comparer", params={"a": "Nantes (44)", "b": "44109"})
    assert page.status_code == 422


def test_api_villes(client):
    reponse = client.get("/api/villes", params={"q": "ren"})
    assert [v["nom"] for v in reponse.json()] == ["Rennes"]


def test_api_ville(client):
    corps = client.get("/api/ville/44109").json()
    assert corps["indicateurs"]["population"]["valeur"] == 327734
    assert client.get("/api/ville/00000").status_code == 404
