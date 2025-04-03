"""
Point d'entrée spécifique pour le workflow Discord Bot Runner.
Ce fichier est utilisé par la configuration du workflow Discord Bot Runner.
"""

import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
import sys

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Discord Bot Runner")

print("Démarrage du bot Discord via discord_bot_workflow.py...")

# Chargement des variables d'environnement
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Vérification du token
if not TOKEN:
    logger.error("ERREUR: Token Discord non trouvé dans les variables d'environnement")
    sys.exit(1)

# Configuration des intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Création du bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Liste des modules d'extension (cogs) à charger
initial_extensions = [
    'cogs.resources',
    # Autres modules à venir
]

@bot.event
async def on_ready():
    logger.info(f"Connecté en tant que {bot.user.name}")
    logger.info(f"ID du bot: {bot.user.id}")
    logger.info("------")
    
    # Définir une activité pour le bot
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, 
        name="les artistes | !help"
    ))

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="général")
    if channel:
        await channel.send(f"Bienvenue {member.mention} dans **Le Séminaire** ! "
                         f"Présente-toi dans #présentation-artistes \U0001f525")

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    await ctx.send("Configuration du serveur en cours...")
    guild = ctx.guild
    
    # Rôles à créer
    roles_to_create = ["Artiste", "Mentor", "Admin", "Membre", "Résident"]
    
    # Créer les rôles
    for role in roles_to_create:
        if not discord.utils.get(guild.roles, name=role):
            await guild.create_role(name=role)
    
    await ctx.send("Le serveur a été configuré avec succès !")

@bot.command()
async def residence(ctx):
    await ctx.send("Prochaines résidences :\n- Concarneau : 21 au 26 juillet 2025")

@bot.command()
async def thibaverse(ctx):
    await ctx.send("Bienvenue dans le Thibaverse ✨ Chaque dimension cache une vérité artistique.")

async def load_extensions():
    for extension in initial_extensions:
        try:
            await bot.load_extension(extension)
            logger.info(f"Extension '{extension}' chargée avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'extension '{extension}': {e}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

# Point d'entrée pour exécuter le bot
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot arrêté manuellement")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du bot: {e}")
        sys.exit(1)