"""
LeSéminaire[BOT] - Point d'entrée principal unifié
Ce fichier sert de point d'entrée pour l'application web Flask via Gunicorn
ou pour le bot Discord selon le workflow utilisé.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("LeSéminaire[BOT]")

# Vérifier si le script est lancé depuis le workflow Discord Bot Runner
is_discord_bot = os.environ.get('REPL_SLUG') and 'discord' in os.environ.get('REPL_SLUG', '').lower()
is_discord_workflow = False

# Si nous sommes dans un workflow, vérifions son nom
if 'REPL_SLUG' in os.environ:
    logger.info(f"REPL_SLUG: {os.environ.get('REPL_SLUG')}")
    if 'discord' in os.environ.get('REPL_SLUG', '').lower():
        is_discord_workflow = True
        logger.info("Démarrage en mode Bot Discord (basé sur le nom du workflow)")
import sys
import os
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Fonction pour démarrer le bot Discord
def run_discord_bot():
    print("Démarrage du bot Discord LeSéminaire...")
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
        return
    
    # Intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    
    # Bot setup
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    # Créer une nouvelle instance du bot plutôt que d'utiliser celle de discord_bot.py
    # Les commandes seront définies directement dans ce script
    
    @bot.event
    async def on_ready():
        print(f"Connecté en tant que {bot.user.name}")
        print(f"ID du bot: {bot.user.id}")
        print("------")
    
    @bot.event
    async def on_member_join(member):
        channel = discord.utils.get(member.guild.text_channels, name="général")
        if channel:
            await channel.send(f"Bienvenue {member.mention} dans **Le Séminaire** ! Présente-toi dans #présentation-artistes \U0001f525")
    
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
    async def art_resources(ctx):
        await ctx.send("Ressources utiles :\n- SACEM : https://www.sacem.fr\n- Intermittence : https://www.cnc.fr/intermittents\n- Thibaverse : https://linktr.ee/thibaees")
    
    @bot.command()
    async def thibaverse(ctx):
        await ctx.send("Bienvenue dans le Thibaverse ✨ Chaque dimension cache une vérité artistique.")
    
    # Démarrage du bot
    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("ERREUR: Échec de connexion à Discord. Vérifiez que votre token est valide.")
    except Exception as e:
        print(f"ERREUR lors du démarrage du bot Discord: {e}")

# Fonction pour démarrer l'application web
    return app  # Pour Gunicorn

# Point d'entrée principal
if __name__ == "__main__":
    # Détecter dans quel workflow nous sommes
    import sys
    program_name = sys.argv[0] if len(sys.argv) > 0 else ""
    
    # Si le programme est lancé directement, sans arguments, déterminer le mode
    # en fonction du workflow en cours d'exécution
    if len(sys.argv) <= 1:
        # Si nous sommes dans le workflow "Discord Bot Runner", démarrer le bot Discord
        if os.environ.get("DISCORD_BOT") == "1" or os.environ.get("RUN_DISCORD_BOT") == "1":
            run_discord_bot()
  
    else:
        # Si des arguments sont fournis, les traiter comme avant
        if sys.argv[1] == "bot":
            # Mode bot Discord
            run_discord_bot()
     
