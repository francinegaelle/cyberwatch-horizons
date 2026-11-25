# Publication dynamique sur Render

Le site GitHub Pages peut rester disponible, mais la version à remettre à la professeure
doit être le **Web Service Render**, car celui-ci exécute réellement Flask côté serveur.

## Fichiers ajoutés
- `app.py` : backend Flask et API dynamique.
- `templates/index.html` : interface dynamique.
- `render.yaml` : configuration Render.
- `requirements.txt` : ajout Flask + Gunicorn.

## API dynamique
- `/api/health` : vérifie que le backend fonctionne.
- `/api/summary` : résumé, catégories, sources et KPI.
- `/api/events` : recherche et filtrage côté serveur.
- `/api/refresh` : collecte réellement les sources depuis le serveur Render.
- `/api/live-search?q=...` : actualise puis effectue une recherche.
- `/api/notification-status` : indique si le SMTP Render est configuré, sans exposer les secrets.

## Déploiement Render
1. Pousser ces fichiers dans le dépôt GitHub `francinegaelle/cyberwatch-horizons`.
2. Aller sur https://dashboard.render.com/
3. `New` → `Web Service`.
4. Connecter GitHub et choisir `cyberwatch-horizons`.
5. Render peut détecter `render.yaml`, ou utiliser :
   - Runtime : Python 3
   - Build Command : `pip install -r requirements.txt`
   - Start Command : `gunicorn app:app --workers 2 --threads 4 --timeout 120`
6. Plan Free pour le devoir.
7. Après le déploiement, Render fournit un lien `https://...onrender.com`.

## Emails
Les emails P1/P2, H2 hebdomadaires et H3 mensuels peuvent continuer à être envoyés
par les GitHub Actions déjà présentes. Les secrets SMTP restent dans GitHub :
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_EMAIL`.

On peut aussi ajouter les mêmes variables dans Render si l'on veut faire des tests
d'email depuis le backend, mais ce n'est pas nécessaire pour la collecte automatique.
