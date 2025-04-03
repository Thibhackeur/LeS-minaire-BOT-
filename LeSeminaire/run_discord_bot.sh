#!/bin/bash
# Script pour assigner une variable d'environnement et démarrer le bot Discord

# Définir la variable d'environnement pour indiquer qu'on veut lancer le bot Discord
export DISCORD_BOT=1

# Démarrer le bot via le script principal
echo "Démarrage du bot Discord via main.py..."
python main.py