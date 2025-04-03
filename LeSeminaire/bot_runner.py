"""
Point d'entrée spécifique pour le bot Discord.
Ce fichier démarre uniquement le bot Discord.
"""
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Bot setup
bot = commands.Bot(command_prefix="!", intents=intents)

# Import des fonctions depuis discord_bot.py
from discord_bot import on_ready, on_member_join, setup, residence, resources, thibaverse

# Assigner les fonctions au bot
bot.event(on_ready)
bot.event(on_member_join)
bot.command()(setup)
bot.command()(residence)
bot.command()(resources)
bot.command()(thibaverse)

# Point d'entrée pour démarrer le bot
if __name__ == "__main__":
    bot.run(TOKEN)