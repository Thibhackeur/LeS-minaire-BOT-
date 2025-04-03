"""
Script pour exécuter le bot Discord LeSéminaire.
Ce script définit la variable d'environnement DISCORD_BOT=1 puis lance
le bot Discord directement depuis ce fichier.
"""
import sys
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging

# Définir explicitement la variable d'environnement
os.environ["DISCORD_BOT"] = "1"
os.environ["RUN_DISCORD_BOT"] = "1"

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LeSéminaireBOT")

# Chargement des variables d'environnement
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Vérification du token
if not TOKEN:
    logger.error("Token Discord non trouvé. Assurez-vous d'avoir un fichier .env avec la variable DISCORD_TOKEN.")
    sys.exit(1)

# Configuration des intents (permissions) du bot
intents = discord.Intents.default()
intents.message_content = True  # Pour lire le contenu des messages
intents.members = True  # Pour avoir accès aux événements liés aux membres

# Création du bot avec un préfixe "!" pour les commandes
bot = commands.Bot(command_prefix="!", intents=intents)

# Liste des modules d'extension (cogs) à charger
initial_extensions = [
    'cogs.resources',
    # Autres modules à venir
]

@bot.event
async def on_ready():
    """Appelé lorsque le bot est connecté et prêt"""
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
    """Appelé lorsqu'un membre rejoint le serveur"""
    # Trouver le salon "général" pour envoyer un message de bienvenue
    channel = discord.utils.get(member.guild.text_channels, name="général")
    if channel:
        await channel.send(f"Bienvenue {member.mention} dans **Le Séminaire** ! "
                         f"Présente-toi dans #présentation-artistes \U0001f525")

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """Configure les éléments de base du serveur (rôles, salons)"""
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
    """Affiche les informations sur les prochaines résidences artistiques"""
    await ctx.send("Prochaines résidences :\n- Concarneau : 21 au 26 juillet 2025")

@bot.command()
async def thibaverse(ctx):
    """Affiche des informations sur le Thibaverse"""
    await ctx.send("Bienvenue dans le Thibaverse ✨ Chaque dimension cache une vérité artistique.")

async def load_extensions():
    """Charge tous les modules d'extension (cogs) du bot"""
    for extension in initial_extensions:
        try:
            await bot.load_extension(extension)
            logger.info(f"Extension '{extension}' chargée avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'extension '{extension}': {e}")

async def main():
    """Fonction principale pour démarrer le bot"""
    async with bot:
        # Charger les extensions avant de démarrer le bot
        await load_extensions()
        # Démarrer le bot avec le token
        await bot.start(TOKEN)

if __name__ == "__main__":
    # Exécuter la fonction principale dans la boucle d'événements asyncio
    print("Démarrage du bot Discord LeSéminaire via run_discord_bot.py...")
    asyncio.run(main())