# CyberWatch Horizons — version alignée avec le cours de veille

Cette version applique les attentes décrites dans le support de stratégie de veille :

- objectifs SMART par horizon H1/H2/H3 ;
- QMS (Quality Measurement System) ;
- KPI de pertinence, qualité, recoupement, intérêt, utilité et multilingue ;
- seuils/SLO et plan d'amélioration continue ;
- base de connaissances centralisée ;
- historique KPI ;
- automatisation ;
- tableau de bord ;
- signaux faibles ;
- scénarios H3 ;
- alertes email.

## Tes objectifs

- H1 : Veille CVE et correctifs de sécurité — quotidien / continu.
- H2 : Évolution IAM et Zero Trust — hebdomadaire.
- H3 : IA en cybersécurité — mensuelle.

Le moteur ne se limite PAS à ces trois sujets. Il collecte aussi les incidents IT mondiaux :
vulnérabilités, cyberattaques, pannes cloud/SaaS, DevOps/supply chain, réseaux, réglementation et nouveautés technologiques.

## Sources initiales

CISA KEV, NVD/NIST, CERT-FR, Fortinet PSIRT, GitHub Status, Cloudflare Status,
OpenAI Status, Microsoft Security Blog, Google Security Blog.

## Emails automatiques

P1/P2 : immédiatement lors de la collecte suivante.
H2 : synthèse hebdomadaire.
H3 : synthèse mensuelle.

### Secrets GitHub à créer

Settings > Secrets and variables > Actions > New repository secret

- SMTP_HOST
- SMTP_PORT
- SMTP_USER
- SMTP_PASSWORD
- ALERT_EMAIL
- NVD_API_KEY (optionnel mais recommandé)

### Gmail
SMTP_HOST = smtp.gmail.com
SMTP_PORT = 587
SMTP_USER = votre adresse Gmail
SMTP_PASSWORD = mot de passe d'application Google
ALERT_EMAIL = adresse destinataire

## GitHub Pages

Settings > Pages > Source = GitHub Actions

Puis lancer :
Actions > CyberWatch - collecte mondiale et alertes > Run workflow

## KPI

Chaque horizon possède ses propres seuils SMART.
Si un KPI n'atteint pas son objectif, l'interface affiche le plan d'action SLA correspondant.

## Attention

Aucun outil ne peut garantir 100 % de tous les incidents informatiques mondiaux.
Le dispositif vise une couverture large et extensible avec plusieurs sources officielles et
des sources techniques reconnues.
