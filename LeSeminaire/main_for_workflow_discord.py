"""
Point d'entrée spécifique pour le workflow Discord Bot Runner.
Ce fichier est le point d'entrée qui sera appelé par le workflow Discord Bot Runner.
"""

import os
import sys
import runpy

print("Démarrage du bot Discord via main_for_workflow_discord.py...")
# Exécuter le fichier workflow_discord_bot.py
runpy.run_path("workflow_discord_bot.py")