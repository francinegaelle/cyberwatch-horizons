# Mise à jour — Centre de notifications intégré au site

Cette version déplace la configuration utilisateur des alertes DANS CyberWatch.

## Dans l'onglet Alertes du site
L'utilisateur peut :
- saisir l'adresse destinataire ;
- activer/désactiver les emails ;
- activer P1 immédiat ;
- activer P2 immédiat ;
- activer le digest H2 hebdomadaire ;
- activer le digest H3 mensuel ;
- demander les notifications navigateur ;
- enregistrer les préférences ;
- envoyer un email de test ;
- consulter l'historique des emails automatiques.

## Secrets techniques à configurer une seule fois sur Render
Ces valeurs ne doivent PAS être exposées dans le site :
- RESEND_API_KEY : clé API Resend.
- ALERT_FROM_EMAIL : expéditeur autorisé par Resend. Pour les premiers tests, utiliser un expéditeur autorisé par votre compte Resend.
- ADMIN_PIN : code de votre choix pour empêcher un visiteur de modifier les préférences.
- DATABASE_URL : URL d'une base PostgreSQL Render pour conserver les préférences et l'historique.

Pourquoi une API email et pas Gmail SMTP ?
Le plan Free de Render bloque les ports SMTP classiques 25, 465 et 587. Une API HTTPS d'email fonctionne sur le port 443.

## Base PostgreSQL
Créer sur Render :
New > Postgres > Free.
Puis connecter/copier l'Internal Database URL dans la variable DATABASE_URL du service Web CyberWatch.
La base gratuite Render convient à une démonstration mais expire actuellement après 30 jours.

## Resend
Créer un compte sur https://resend.com
Créer une API key, puis la mettre dans RESEND_API_KEY sur Render.
Pour envoyer à des destinataires arbitraires, utiliser un domaine expéditeur vérifié selon les règles du fournisseur.

## Automatisation
Le workflow `.github/workflows/site-alert-scheduler.yml` appelle le site toutes les 15 minutes :
https://cyberwatch-horizons.onrender.com/api/scheduled-check

Le backend :
1. actualise les sources ;
2. vérifie P1/P2 ;
3. consulte les préférences enregistrées depuis le site ;
4. évite les doublons grâce à PostgreSQL ;
5. envoie l'email via l'API HTTPS ;
6. produit les digests H2/H3 aux échéances prévues.
