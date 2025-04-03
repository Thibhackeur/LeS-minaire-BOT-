"""
LeSéminaire[BOT] - Lanceur dédié pour le bot Discord
Ce fichier est exclusivement dédié au lancement du bot Discord.
"""
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Vérification du token
if not TOKEN:
    print("ERREUR: Token Discord non trouvé. Vérifiez votre fichier .env")
    exit(1)

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Bot setup
bot = commands.Bot(command_prefix="!", intents=intents)

# Import du module discord_bot
from discord_bot import on_ready, on_member_join, setup, residence, resources, thibaverse

# Assigner les events et commandes au bot
bot.event(on_ready)
bot.event(on_member_join)
bot.command()(setup)
bot.command()(residence)
bot.command()(resources)
bot.command()(thibaverse)

# Point d'entrée principal
if __name__ == "__main__":
    print("Démarrage du bot Discord LeSéminaire...")
    bot.run(TOKEN)