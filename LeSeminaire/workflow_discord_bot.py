"""
Ce fichier est spécialement conçu pour être utilisé par le workflow Discord Bot Runner.
Il est indépendant des autres fichiers du projet et gère uniquement le bot Discord.
"""

# ===================== IMPORTS =====================
import os
import sys
import asyncio
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv
from enum import Enum
import datetime

# ===================== LOGGING SETUP =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("Discord Bot Runner")

# ===================== LOAD ENVIRONMENT VARIABLES =====================
print("Démarrage du bot Discord LeSéminaire via workflow_discord_bot.py...")
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    logger.error("Token Discord non trouvé dans le fichier .env")
    sys.exit(1)

# ===================== BOT CONFIGURATION =====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===================== RESOURCES COG =====================
class ResourceType(Enum):
    SACEM = 1
    INTERMITTENCE = 2
    FORMATION = 3
    PROMO = 4
    PRESSE = 5
    MATERIEL = 6
    INSPIRATION = 7
    AUTRE = 8

class ResourceCog(commands.Cog):
    """Gestion des ressources artistiques partagées par la communauté"""
    
    def __init__(self, bot):
        self.bot = bot
        self.resources_list = [
            {
                "nom": "SACEM",
                "url": "https://www.sacem.fr",
                "description": "Société des auteurs, compositeurs et éditeurs de musique",
                "type": ResourceType.SACEM,
                "added_by": "LeSéminaire[BOT]",
                "date_added": datetime.datetime.now().strftime("%d/%m/%Y")
            },
            {
                "nom": "Intermittence",
                "url": "https://www.cnc.fr/intermittents",
                "description": "Informations sur le statut d'intermittent du spectacle",
                "type": ResourceType.INTERMITTENCE,
                "added_by": "LeSéminaire[BOT]",
                "date_added": datetime.datetime.now().strftime("%d/%m/%Y")
            },
            {
                "nom": "Thibaverse",
                "url": "https://linktr.ee/thibaees",
                "description": "Univers créatif multidimensionnel de Thibaees",
                "type": ResourceType.INSPIRATION,
                "added_by": "LeSéminaire[BOT]",
                "date_added": datetime.datetime.now().strftime("%d/%m/%Y")
            }
        ]
    
    @commands.command(name="art_resources")
    async def resources(self, ctx):
        """Affiche la liste des ressources artistiques disponibles"""
        
        embed = discord.Embed(
            title="📚 Ressources artistiques",
            description="Liste des ressources utiles pour les artistes",
            color=discord.Color.blue()
        )
        
        # Regrouper les ressources par type
        resources_by_type = {}
        for resource in self.resources_list:
            type_name = resource["type"].name
            if type_name not in resources_by_type:
                resources_by_type[type_name] = []
            resources_by_type[type_name].append(resource)
        
        # Ajouter chaque type de ressource comme un champ de l'embed
        for type_name, resources_list in resources_by_type.items():
            value = ""
            for resource in resources_list:
                value += f"[{resource['nom']}]({resource['url']}): {resource['description']}\n"
            embed.add_field(name=f"✨ {type_name.capitalize()}", value=value, inline=False)
            
        embed.set_footer(text="Utilisez !add_resource pour ajouter une ressource")
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def add_resource(self, ctx, nom, url, type_resource, *, description=""):
        """Ajoute une nouvelle ressource artistique
        
        Arguments:
            nom: Nom de la ressource
            url: URL de la ressource
            type_resource: Type de ressource (SACEM, INTERMITTENCE, FORMATION, PROMO, PRESSE, MATERIEL, INSPIRATION, AUTRE)
            description: Description de la ressource (optionnel)
        """
        try:
            # Vérifier que le type existe
            resource_type = ResourceType[type_resource.upper()]
            
            # Ajouter la ressource
            self.resources_list.append({
                "nom": nom,
                "url": url,
                "description": description,
                "type": resource_type,
                "added_by": str(ctx.author),
                "date_added": datetime.datetime.now().strftime("%d/%m/%Y")
            })
            
            await ctx.send(f"Ressource **{nom}** ajoutée avec succès !")
            
        except KeyError:
            # Si le type n'existe pas
            valid_types = ", ".join([t.name for t in ResourceType])
            await ctx.send(f"Type de ressource invalide. Types disponibles: {valid_types}")
    
    @commands.command()
    async def find_resource(self, ctx, *, query):
        """Recherche une ressource par mot-clé dans le nom ou la description"""
        
        query = query.lower()
        results = []
        
        for resource in self.resources_list:
            if (query in resource["nom"].lower() or 
                query in resource["description"].lower()):
                results.append(resource)
        
        if results:
            embed = discord.Embed(
                title=f"🔍 Résultats pour '{query}'",
                description=f"{len(results)} ressource(s) trouvée(s)",
                color=discord.Color.green()
            )
            
            for resource in results:
                embed.add_field(
                    name=f"{resource['nom']} ({resource['type'].name})",
                    value=f"[Lien]({resource['url']})\n{resource['description']}\nAjouté par: {resource['added_by']}",
                    inline=False
                )
                
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Aucune ressource trouvée pour '{query}'")

# ===================== BOT EVENTS =====================
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

# ===================== BOT COMMANDS =====================
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

# ===================== MAIN FUNCTION =====================
async def main():
    """Fonction principale pour démarrer le bot"""
    async with bot:
        # Ajouter le cog de ressources
        await bot.add_cog(ResourceCog(bot))
        # Démarrer le bot avec le token
        await bot.start(TOKEN)

# ===================== ENTRY POINT =====================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot arrêté manuellement")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du bot: {e}")
        sys.exit(1)