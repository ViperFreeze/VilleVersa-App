"""Crée data/villes.csv : les communes de plus de 20 000 habitants (API Géo).

Lancement depuis la racine du projet :  python -m scripts.preparer_villes
"""
import logging
import sys

from app.services import geo


def main() -> None:
    # Affiche les avertissements des services (cause exacte d'un appel échoué).
    logging.basicConfig(level=logging.INFO, format="  %(levelname)s %(message)s")
    print("Demande des communes à l'API Géo, département par département...")
    villes = geo.telecharger_villes()
    if not villes:
        sys.exit(
            "Aucune commune reçue. La cause est affichée juste au-dessus (WARNING).\n"
            "- ConnectTimeout / ConnectError / ProxyError : pas d'accès à geo.api.gouv.fr "
            "(réseau de l'IUT, proxy, pare-feu ?). Essayez depuis un autre réseau "
            "(partage de connexion du téléphone).\n"
            "- SSL / certificate : le réseau intercepte le HTTPS ; même solution.\n"
            "- ReadTimeout : l'API est lente, relancez le script."
        )
    geo.enregistrer_villes(villes)
    print(f"{len(villes)} villes de plus de {geo.SEUIL_POPULATION:,} habitants écrites dans {geo.FICHIER_VILLES}")


if __name__ == "__main__":
    main()
