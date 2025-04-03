"""
Script dédié au lancement du bot Discord LeSéminaire.
Ce script définit explicitement la variable d'environnement RUN_DISCORD_BOT
pour s'assurer que le bot démarre correctement.
"""

import os
import sys

# Définir explicitement la variable d'environnement pour indiquer que
# nous voulons exécuter le bot Discord et non l'application web
os.environ["RUN_DISCORD_BOT"] = "1"

# Importer le script principal
try:
    print("Démarrage du bot Discord LeSéminaire...")
    from main import run_discord_bot
    # Exécuter la fonction de démarrage du bot
    run_discord_bot()
except Exception as e:
    print(f"Erreur lors du démarrage du bot Discord: {e}")
    sys.exit(1)