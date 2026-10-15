"""Profils utilisateur et catalogue des indicateurs.

Tout le paramétrage de la comparaison est ici : ajouter un indicateur ou
modifier un profil ne demande de toucher à aucun autre fichier.
"""
from dataclasses import dataclass

# Onglets possibles, dans l'ordre d'affichage par défaut.
THEMES = {
    "general": "Informations générales",
    "emploi": "Emploi",
    "logement": "Logement",
    "meteo": "Météo",
    "formation": "Formation",
    "equipements": "Équipements",
    "transports": "Transports",
}

# Les quatre thèmes imposés par la consigne : présents pour tous les profils.
THEMES_OBLIGATOIRES = ("general", "emploi", "logement", "meteo")


@dataclass(frozen=True)
class Indicateur:
    id: str
    libelle: str
    theme: str
    unite: str = ""
    source: str = ""
    format: str = "{:,.0f}"  # format Python, converti à la française à l'affichage


INDICATEURS = {
    i.id: i
    for i in [
        # Informations générales
        Indicateur("population", "Population", "general", "hab.", "API Géo"),
        Indicateur("surface_km2", "Superficie", "general", "km²", "API Géo", "{:,.1f}"),
        Indicateur("densite", "Densité", "general", "hab./km²", "Calcul"),
        Indicateur("departement", "Département", "general", "", "API Géo", "{}"),
        Indicateur("region", "Région", "general", "", "API Géo", "{}"),
        # Emploi
        Indicateur("taux_chomage", "Taux de chômage", "emploi", "%", "Insee", "{:.1f}"),
        # France Travail : statistiques départementales (pas de données communales)
        Indicateur("offres_pour_100_demandeurs", "Offres sur 12 mois pour 100 demandeurs (département)",
                   "emploi", "", "France Travail, calcul"),
        Indicateur("offres_12_mois_dep", "Offres d'emploi déposées sur 12 mois (département)",
                   "emploi", "offres", "France Travail"),
        Indicateur("demandeurs_a_dep", "Demandeurs d'emploi, catégorie A (département)",
                   "emploi", "personnes", "France Travail"),
        Indicateur("salaries_dep", "Salariés (département)", "emploi", "salariés", "France Travail"),
        Indicateur("dynamisme_emploi_dep", "Indicateur de dynamisme de l'emploi (département)",
                   "emploi", "", "France Travail", "{:.1f}"),
        # Logement
        Indicateur("loyer_m2_appartement", "Loyer d'annonce, appartement", "logement", "€/m²", "ANIL", "{:.1f}"),
        Indicateur("loyer_m2_t1t2", "Loyer d'annonce, T1-T2", "logement", "€/m²", "ANIL", "{:.1f}"),
        Indicateur("loyer_m2_t3plus", "Loyer d'annonce, T3 et plus", "logement", "€/m²", "ANIL", "{:.1f}"),
        Indicateur("loyer_m2_maison", "Loyer d'annonce, maison", "logement", "€/m²", "ANIL", "{:.1f}"),
        Indicateur("prix_m2_appartement", "Prix de vente médian, appartement", "logement", "€/m²", "DVF"),
        Indicateur("prix_m2_maison", "Prix de vente médian, maison", "logement", "€/m²", "DVF"),
        # Météo (climat à l'année ; les prévisions sont un graphique à part)
        Indicateur("temp_moy_annuelle", "Température moyenne annuelle", "meteo", "°C", "Open-Meteo", "{:.1f}"),
        Indicateur("precip_annuelles", "Précipitations annuelles", "meteo", "mm", "Open-Meteo"),
        Indicateur("ensoleillement_annuel", "Ensoleillement annuel", "meteo", "h", "Open-Meteo"),
        # Thèmes propres à un profil
        Indicateur("nb_etudiants", "Étudiants inscrits", "formation", "étudiants", "MESR"),
        # France Travail, Cadre de vie des communes (eTerritoire) : données communales
        Indicateur("equip_education", "Équipements d'éducation", "equipements", "", "France Travail, eTerritoire"),
        Indicateur("equip_sante", "Équipements de santé", "equipements", "", "France Travail, eTerritoire"),
        Indicateur("equip_sport", "Équipements sportifs", "equipements", "", "France Travail, eTerritoire"),
        Indicateur("equip_loisirs", "Équipements de loisirs", "equipements", "", "France Travail, eTerritoire"),
        Indicateur("equip_services_publics", "Services publics", "equipements", "", "France Travail, eTerritoire"),
        Indicateur("frequentation_gares", "Voyageurs en gare par an", "transports", "voyageurs", "SNCF"),
    ]
}


@dataclass(frozen=True)
class Profil:
    id: str
    libelle: str
    question: str
    themes: tuple[str, ...]  # ordre des onglets
    mis_en_avant: tuple[str, ...]  # indicateurs affichés en tête de leur onglet


PROFILS = {
    p.id: p
    for p in [
        Profil(
            "etudiant", "Étudiant", "Où faire mes études ?",
            ("general", "formation", "logement", "emploi", "meteo"),
            ("nb_etudiants", "loyer_m2_t1t2"),
        ),
        Profil(
            "jeune_actif", "Jeune actif", "Où m'installer pour travailler ?",
            ("general", "emploi", "logement", "meteo"),
            ("offres_pour_100_demandeurs", "dynamisme_emploi_dep", "taux_chomage", "loyer_m2_appartement"),
        ),
        Profil(
            "famille", "Famille", "Où s'installer avec des enfants ?",
            ("general", "logement", "equipements", "emploi", "meteo"),
            ("loyer_m2_t3plus", "loyer_m2_maison", "prix_m2_maison", "equip_education"),
        ),
        Profil(
            "qualite_vie", "Qualité de vie", "Où vit-on le mieux ?",
            ("general", "meteo", "logement", "transports", "emploi"),
            ("ensoleillement_annuel", "temp_moy_annuelle", "frequentation_gares", "prix_m2_appartement"),
        ),
    ]
}

PROFIL_PAR_DEFAUT = "etudiant"


def indicateurs_du_theme(profil: Profil, theme: str) -> list[Indicateur]:
    """Indicateurs d'un thème, ceux que le profil met en avant en premier."""
    rang = {iid: n for n, iid in enumerate(profil.mis_en_avant)}
    du_theme = [i for i in INDICATEURS.values() if i.theme == theme]
    # Tri stable : les autres indicateurs gardent l'ordre du catalogue.
    return sorted(du_theme, key=lambda i: rang.get(i.id, len(rang)))
