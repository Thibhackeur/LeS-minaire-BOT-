"""
LeSéminaire[BOT] - Bot Discord pour la communauté artistique "Le Séminaire"
Auteur: LeSéminaire
Date: Avril 2025

Ce bot facilite la gestion communautaire, propose des ressources artistiques
et offre des outils de collaboration pour les artistes.
"""
import os
import asyncio
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv
from help_command import HelpCommand
from database import db_manager

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('le_seminaire_bot')

# Charger les variables d'environnement
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Vérifier si le token est disponible
if not TOKEN:
    logger.error("Token Discord non trouvé. Veuillez définir DISCORD_TOKEN dans le fichier .env")
    exit(1)

# Configuration des intents Discord (autorisations nécessaires)
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True
intents.reactions = True

# Créer le bot avec ses intents et son préfixe de commande
bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    case_insensitive=True,
    help_command=HelpCommand()
)

# Liste des modules (cogs) à charger au démarrage
INITIAL_EXTENSIONS = [
    'cogs.resources',
    'cogs.music',
    'cogs.collaborations',
    'cogs.security',   # Module anti-spam et protection contre les raids
    'cogs.shield',     # Module bouclier (protection DDos, anti-bot, etc.)
    'cogs.messenger',  # Module de messagerie directe (annonces, bienvenue, événements)
    'cogs.analytics'   # Module d'analytique et visualisation d'engagement
]

# Événement: Le bot est prêt et connecté
@bot.event
async def on_ready():
    """Appelé lorsque le bot est connecté et prêt"""
    logger.info(f"{bot.user.name} est connecté à Discord!")
    
    # Définir le statut du bot
    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name="!help | Le Séminaire"
    )
    await bot.change_presence(activity=activity)
    
    # Afficher des informations sur les serveurs connectés
    guild_count = len(bot.guilds)
    member_count = sum(g.member_count for g in bot.guilds)
    logger.info(f"Le bot est présent sur {guild_count} serveurs avec un total de {member_count} membres.")
    
    for guild in bot.guilds:
        logger.info(f"- {guild.name} (ID: {guild.id}) - {guild.member_count} membres")

# Événement: Message reçu
@bot.event
async def on_message(message):
    """Appelé lorsqu'un message est envoyé"""
    # Ignorer les messages du bot
    if message.author.bot:
        return
    
    # Traiter les commandes (nécessaire lorsqu'on surcharge on_message)
    await bot.process_commands(message)

# Charger les cogs (modules d'extension)
async def load_extensions():
    """Charge tous les modules d'extension (cogs) du bot"""
    for extension in INITIAL_EXTENSIONS:
        try:
            await bot.load_extension(extension)
            logger.info(f"Module chargé: {extension}")
        except Exception as e:
            logger.error(f"Échec du chargement du module {extension}: {e}")

# Démarrage du bot
async def main():
    """Fonction principale pour démarrer le bot"""
    # Initialiser la base de données
    logger.info("Initialisation de la base de données...")
    
    # Charger les extensions
    logger.info("Chargement des modules...")
    await load_extensions()
    
    # Connexion au Discord
    logger.info("Connexion à Discord...")
    await bot.start(TOKEN)

# Point d'entrée pour le démarrage direct du bot
if __name__ == "__main__":
    asyncio.run(main())