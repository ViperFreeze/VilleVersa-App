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

**Identifiants France Travail** (facultatifs en local) : copier `.env.example` en
`.env` à la racine et y mettre `FT_CLIENT_ID` et `FT_CLIENT_SECRET`. Le fichier
`.env` est ignoré par git. Sans lui, l'onglet Emploi affiche « — ».

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
| Open-Meteo, climat | Script `preparer_climat` | Lancer le script (~2 h, peut-être sur deux jours à cause des quotas ; il reprend où il s'est arrêté) |
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

## Mettre en ligne sur Render

Le fichier `render.yaml` décrit le service (offre gratuite, Python 3.13 via
`.python-version`). Streamlit Community Cloud ne convient pas : il ne lance que
des scripts Streamlit, pas un serveur FastAPI.

1. En local, préparer les données puis les pousser sur GitHub :
   `data/villes.csv`, `data/climat_mensuel.csv` et `data/indicateurs/*.csv`
   (jamais `data/sources/` ni `.env`).
2. Sur https://render.com, se connecter avec GitHub, puis **New > Blueprint**
   et choisir le dépôt `VilleVersa-App`.
3. Render demande `FT_CLIENT_ID` et `FT_CLIENT_SECRET` : coller les valeurs du `.env`.
4. Valider. L'appli est en ligne sur `https://villeversa.onrender.com`
   (ou un nom proche si celui-ci est pris). Chaque `git push` sur `main` la redéploie.

Offre gratuite : l'appli s'endort après 15 min sans visite et met environ une
minute à se réveiller. L'ouvrir quelques minutes avant une démonstration.

## Licences à citer

Insee (Licence Ouverte 2.0) · API Géo, DINUM · France Travail · ANIL, « Estimations
ANIL, à partir des données du Groupe SeLoger et de leboncoin » (Licence Ouverte 2.0) ·
DVF (Licence Ouverte 2.0) · Open-Meteo (CC BY 4.0, usage non commercial) ·
Wikipédia (CC BY-SA 4.0) · SNCF Gares & Connexions (ODbL).
