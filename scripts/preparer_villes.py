"""Crée data/villes.csv : les communes de plus de 20 000 habitants (API Géo).

Lancement depuis la racine du projet :  python -m scripts.preparer_villes
"""
import sys

from app.services import geo


def main() -> None:
    print("Demande de toutes les communes à l'API Géo...")
    villes = geo.telecharger_villes()
    if not villes:
        sys.exit("Aucune commune reçue : vérifiez la connexion à geo.api.gouv.fr.")
    geo.enregistrer_villes(villes)
    print(f"{len(villes)} villes de plus de {geo.SEUIL_POPULATION:,} habitants écrites dans {geo.FICHIER_VILLES}")


if __name__ == "__main__":
    main()
