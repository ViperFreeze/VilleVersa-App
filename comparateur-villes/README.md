# Comparateur de villes

Application web qui compare deux villes françaises de plus de 20 000 habitants,
selon le profil de l'utilisateur : étudiant, jeune actif, famille ou qualité de vie.

- **Backend** : Python, FastAPI. Toute la logique est en Python : appels aux API,
  lecture des fichiers, calculs, graphiques Plotly.
- **Front** : pages HTML générées par le serveur (Jinja2), une feuille CSS, et
  quelques lignes de JavaScript pour les onglets et l'affichage des graphiques.

## Lancer en local

```bash
python -m venv .venv
source .venv/bin/activate            # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python -m scripts.preparer_villes    # crée data/villes.csv (une fois)
uvicorn app.main:app --reload
```

Puis ouvrir http://127.0.0.1:8000. La documentation de l'API JSON est sur
http://127.0.0.1:8000/docs.

Tests (sans réseau) : `python -m pytest`

## Structure

```
app/
  main.py              routes : pages HTML (/ et /comparer) et API JSON (/api/...)
  graphiques.py        graphiques Plotly construits en Python
  config/profils.py    catalogue des indicateurs + ce que chaque profil met en avant
  services/            une source de données par module
    geo.py             liste des villes et fiche d'identité (API Géo)
    wikipedia.py       résumé et image (Wikipédia)
    meteo.py           prévisions (en direct) et climat (précalculé) (Open-Meteo)
    emploi.py          offres d'emploi (France Travail, identifiants requis)
    statiques.py       lit les tables préparées dans data/indicateurs/
    fiche.py           assemble toutes les données d'une ville
  templates/           pages HTML
  static/              CSS et JavaScript
scripts/               préparation des fichiers statiques
data/
  villes.csv           créé par preparer_villes
  climat_mensuel.csv   créé par preparer_climat
  indicateurs/*.csv    une table par source : colonne `code` + une colonne par indicateur
  sources/             fichiers bruts téléchargés (non versionnés)
tests/                 tests automatiques
```

**Ajouter un indicateur** : le déclarer dans `app/config/profils.py`, puis
produire une colonne du même nom dans un fichier de `data/indicateurs/`.
L'appli l'affiche dans le bon onglet sans autre modification.

## État des sources

| Source | Branchement | À faire |
|---|---|---|
| API Géo | En direct | Rien |
| Wikipédia | En direct | Vérifier le cas des homonymes au premier test |
| Open-Meteo, prévisions | En direct | Rien |
| Open-Meteo, climat | Script `preparer_climat` | Lancer le script (~10 min) |
| France Travail | En direct si identifiants | S'inscrire, renseigner `FT_CLIENT_ID` et `FT_CLIENT_SECRET`, vérifier les paramètres notés en TODO |
| Loyers ANIL et prix DVF | Script `preparer_logement` | Lancer ; confirmer les noms de colonnes |
| Insee (chômage, etc.) | Script `preparer_insee` | Lancer `--explorer`, choisir les codes, remplir `MESURES` |
| Étudiants, BPE, gares | Pas encore | Écrire un script sur le même modèle |

Ordre conseillé :

```bash
python -m scripts.preparer_villes
python -m scripts.preparer_climat --limite 3   # essai, puis sans --limite
python -m scripts.preparer_logement
python -m scripts.preparer_insee --explorer
```

## Mettre en ligne (exemple : Render)

1. Pousser le projet sur GitHub, avec `data/villes.csv`, `data/climat_mensuel.csv`
   et `data/indicateurs/` (pas `data/sources/`).
2. Sur Render, créer un « Web Service » relié au dépôt.
3. Build : `pip install -r requirements.txt`
4. Start : `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Ajouter `FT_CLIENT_ID` et `FT_CLIENT_SECRET` dans les variables d'environnement.

## Licences à citer

Insee (Licence Ouverte 2.0) · API Géo, DINUM · France Travail · ANIL, « Estimations
ANIL, à partir des données du Groupe SeLoger et de leboncoin » (Licence Ouverte 2.0) ·
DVF (Licence Ouverte 2.0) · Open-Meteo (CC BY 4.0, usage non commercial) ·
Wikipédia (CC BY-SA 4.0) · SNCF Gares & Connexions (ODbL).
