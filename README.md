# Projet 70°NORD · Cadeau Surprise des 30 ans de Camille

Application Flask + SQLAlchemy pour la cagnotte participative du voyage du 7 au 17 janvier 2027.

## Draft compilé

- Objectif public : **2 400 €**, correspondant à la part de Camille.
- Catégorie « Visites, transports & imprévus » supprimée.
- Tromsø mutualisé en une seule fiche.
- « MV Quest » remplacé par **Croisière Aurore Boréale et Safari Baleine**.
- Fiches Lofoten, cabane, bus, traversée et Oslo mises à jour.
- « Repas & gourmandises » enrichi avec les photos sucrées et salées sélectionnées.
- Galeries photos intégrées pour la croisière, Oslo et les repas.
- Photos fournies par l'utilisateur copiées dans `static/images/`.
- Prévisualisation statique disponible dans `preview.html`.

## Local

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
set ADMIN_PASSWORD=un-mot-de-passe-fort   # Windows CMD
# ou export ADMIN_PASSWORD=un-mot-de-passe-fort
python app.py
```

Puis ouvrir http://127.0.0.1:5000

Administration : `/admin/login`

## Production

Variables : `SECRET_KEY`, `ADMIN_PASSWORD`, `DATABASE_URL` et éventuellement `PORT`.

Le projet contient un `Procfile` compatible avec Render et autres plateformes Python.

## Données

Les activités sont synchronisées au démarrage de façon non destructive : les anciennes catégories sont masquées et les promesses existantes sont rattachées aux catégories fusionnées lorsque nécessaire.
