# LeSéminaire[BOT]

Un bot Discord conçu pour faciliter la gestion d'une communauté artistique, incluant des outils de modération, de partage de ressources, et de gestion d'événements.

## Fonctionnalités principales

- **Gestion communautaire**: Rôles spécialisés pour artistes, mentors et résidents
- **Structure de serveur automatisée**: Création et organisation de catégories et canaux
- **Système de vérification en deux étapes**: Protection contre les raids et les comptes non vérifiés
- **Partage de ressources artistiques**: Base de données de ressources catégorisées
- **Outil de résidence artistique**: Informations sur les résidences et programmation
- **Modération avancée**: Commandes de modération et protection contre le spam
- **Statistiques et analytiques**: Suivi de l'activité du serveur et des interactions
- **Interface web**: Administration des ressources et des fonctionnalités du bot

## Installation et configuration

1. Clonez ce dépôt 
2. Copiez `.env.example` vers `.env` et configurez vos variables d'environnement
3. Installez les dépendances: `pip install -r requirements.txt`
4. Démarrez le bot: `./start_discord_bot.sh`
5. Démarrez l'interface web: `./start_web_8080.sh`

## Structure du projet

- **bot.py**: Point d'entrée du bot Discord
- **app.py**: Application web Flask 
- **cogs/**: Modules du bot (modération, ressources, etc.)
- **models.py**: Modèles de données SQLAlchemy
- **database.py**: Gestion de la base de données
- **templates/**: Templates HTML pour l'interface web
- **static/**: Fichiers statiques (CSS, JS, images)

## Utilisation

### Bot Discord

Une fois le bot connecté à votre serveur, utilisez la commande `!aide` pour voir la liste des commandes disponibles.

### Interface Web

L'interface web est accessible sur le port 8080 (`http://localhost:8080`) et permet de gérer les ressources artistiques, les samples musicaux et les statistiques du serveur.

## Licence

Ce projet est sous licence MIT.