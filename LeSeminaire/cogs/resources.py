"""
Module d'extension (cog) pour la gestion des ressources artistiques dans le bot LeSéminaire.
Permet de partager, rechercher et organiser des ressources utiles pour les artistes.
"""

import discord
from discord.ext import commands
from enum import Enum
import os
from dotenv import load_dotenv
import datetime

# Chargement des variables d'environnement
load_dotenv()

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
        # Format: {"nom": "url", "description", "type", "added_by", "date_added"}
        self.resources = [
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
        for resource in self.resources:
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
            self.resources.append({
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
        
        for resource in self.resources:
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

# Setup function required for Cogs
async def setup(bot):
    await bot.add_cog(ResourceCog(bot))