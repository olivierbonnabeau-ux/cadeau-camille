# Les 30 ans de Camille — application

Application Flask avec base de données SQLAlchemy. SQLite est utilisé par défaut en local ; en production, définir `DATABASE_URL` vers PostgreSQL.

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

Variables nécessaires : `SECRET_KEY`, `ADMIN_PASSWORD`, `DATABASE_URL` et éventuellement `PORT`.

Le projet contient un `Procfile` compatible avec les plateformes d'hébergement Python courantes. Pour PostgreSQL, utiliser par exemple :
`postgresql+psycopg://USER:PASSWORD@HOST:5432/DB`

## Données

Les tables sont créées automatiquement au premier démarrage. Les activités du Draft 2 sont insérées automatiquement si la base est vide.
