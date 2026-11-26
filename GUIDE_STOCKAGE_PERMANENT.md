# CyberWatch — stockage permanent sans PostgreSQL Render

Cette version garde la même application, mais remplace PostgreSQL Render par un **Gist GitHub secret** pour les préférences et l'historique des alertes.

## Ce qui reste identique
- URL Render et backend Flask.
- H1 / H2 / H3.
- Recherche dynamique et Recherche live.
- KPI / QMS.
- Signaux faibles.
- Flux mondial et sources.
- Centre de notifications.
- Emails P1/P2, synthèses H2/H3.
- Historique des emails.

## Ce qui change
Les données suivantes sont maintenant conservées dans GitHub :
- adresse email destinataire ;
- préférences P1/P2/H2/H3 ;
- historique des alertes envoyées ;
- état anti-doublons du contrôle automatique.

Vous n'avez plus besoin de `DATABASE_URL`.

## Configuration à faire une fois dans Render
Conserver vos variables actuelles :
- `RESEND_API_KEY`
- `ALERT_FROM_EMAIL`
- `ADMIN_PIN`

Ajouter :
- `GITHUB_GIST_TOKEN`

## Créer `GITHUB_GIST_TOKEN`
1. GitHub > photo de profil > Settings.
2. Developer settings.
3. Personal access tokens > Fine-grained tokens.
4. Generate new token.
5. Donner la permission utilisateur **Gists: Read and write**.
6. Copier le token.
7. Render > cyberwatch-horizons > Environment.
8. Ajouter `GITHUB_GIST_TOKEN` avec ce token comme valeur.
9. Save and deploy.

Au premier enregistrement des préférences dans l'onglet Alertes, CyberWatch crée automatiquement un Gist secret contenant `cyberwatch_state.json`. Après chaque redémarrage de Render, le site retrouve automatiquement ce Gist avec le token.

## Important
Un Gist secret est non listé publiquement, mais ce n'est pas un coffre-fort chiffré. Ne partagez jamais son URL. Le token GitHub, la clé Resend et le code administrateur restent uniquement dans les variables d'environnement Render.

## Disponibilité du site
Le Web Service Render gratuit ne disparaît pas après 30 jours. Il peut seulement se mettre en veille après une période d'inactivité et se réveiller lors d'une nouvelle requête. Les données persistantes de ce projet sont désormais indépendantes de la base PostgreSQL Render gratuite.
