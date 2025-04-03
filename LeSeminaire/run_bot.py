"""
Script pour exécuter le bot Discord LeSéminaire.
Ce script appelle main.py avec l'argument 'bot' pour lancer uniquement le bot Discord.
"""
import sys
import os

if __name__ == "__main__":
    print("Démarrage du bot Discord via le script run_bot.py...")
    # Utilisation de sys.argv pour passer l'argument 'bot' à main.py
    # Assurez-vous que rien n'empêche main.py de traiter correctement l'argument
    os.environ["RUN_DISCORD_BOT"] = "1"
    # Appel à main.py avec l'argument bot
    from main import run_discord_bot
    run_discord_bot()