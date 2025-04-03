"""
Module de commandes d'aide pour le bot LeSéminaire.
Fournit des informations détaillées sur les commandes et fonctionnalités du bot.
"""
import discord
from discord.ext import commands
import logging
from typing import Dict, List, Optional, Union, Mapping

logger = logging.getLogger(__name__)

class HelpCommand(commands.HelpCommand):
    """
    Commande d'aide personnalisée pour le bot Le Séminaire.
    """
    
    def __init__(self):
        super().__init__(
            command_attrs={
                "help": "Affiche ce message d'aide",
                "aliases": ["aide", "commands", "commandes"]
            }
        )
    
    async def send_bot_help(self, mapping):
        """
        Affiche l'aide générale avec les catégories.
        """
        embed = discord.Embed(
            title="📚 Aide LeSéminaire[BOT]",
            description=(
                "Bienvenue dans l'aide du bot du Séminaire! Voici les catégories de commandes disponibles.\n"
                "Utilisez `!help <catégorie>` ou `!help <commande>` pour plus de détails."
            ),
            color=0x7289da
        )
        
        # Trier les commandes par cog
        filtered = await self.filter_commands(self.context.bot.commands, sort=True)
        
        # Grouper les commandes par catégorie (cog)
        cogs_dict = {}
        for command in filtered:
            cog_name = command.cog_name or "Autres"
            if cog_name not in cogs_dict:
                cogs_dict[cog_name] = []
            cogs_dict[cog_name].append(command)
        
        # Renommer certaines catégories pour plus de clarté
        display_names = {
            "ResourceCog": "📚 Ressources",
            "MusicCog": "🎵 Musique",
            "CollaborationCog": "🤝 Collaborations",
            "ModerationCog": "🛡️ Modération",
            "None": "⚙️ Autres",
            "Autres": "⚙️ Autres"
        }
        
        # Ajouter les catégories à l'embed
        for cog_name, commands_list in cogs_dict.items():
            display_name = display_names.get(cog_name, cog_name)
            value = ", ".join(f"`{cmd.name}`" for cmd in commands_list)
            embed.add_field(name=display_name, value=value, inline=False)
        
        embed.add_field(
            name="📋 Plus d'informations",
            value=(
                "Pour obtenir des détails sur une commande spécifique, utilisez:\n"
                "`!help <commande>`\n\n"
                "Pour voir toutes les commandes d'une catégorie, utilisez:\n"
                "`!help <catégorie>`"
            ),
            inline=False
        )
        
        embed.set_footer(text="Le Séminaire | Bot de communauté artistique")
        
        await self.get_destination().send(embed=embed)
    
    async def send_command_help(self, command):
        """
        Affiche l'aide pour une commande spécifique.
        """
        embed = discord.Embed(
            title=f"Commande: {command.name}",
            color=0x7289da
        )
        
        # Ajouter la description de la commande
        if command.help:
            embed.description = command.help
        else:
            embed.description = "Aucune description disponible."
        
        # Ajouter la syntaxe
        signature = self.get_command_signature(command)
        embed.add_field(name="Syntaxe", value=f"`{signature}`", inline=False)
        
        # Ajouter les alias
        if command.aliases:
            aliases = ", ".join(f"`{alias}`" for alias in command.aliases)
            embed.add_field(name="Alias", value=aliases, inline=True)
        
        # Ajouter le groupe parent si applicable
        if isinstance(command, commands.Group):
            subcommands = ", ".join(f"`{c.name}`" for c in command.commands)
            embed.add_field(
                name="Sous-commandes", 
                value=subcommands or "Aucune sous-commande",
                inline=False
            )
        
        embed.set_footer(text="Le Séminaire | Bot de communauté artistique")
        
        await self.get_destination().send(embed=embed)
    
    async def send_group_help(self, group):
        """
        Affiche l'aide pour un groupe de commandes.
        """
        embed = discord.Embed(
            title=f"Groupe de commandes: {group.name}",
            color=0x7289da
        )
        
        # Ajouter la description du groupe
        if group.help:
            embed.description = group.help
        else:
            embed.description = "Aucune description disponible."
        
        # Filtrer et trier les sous-commandes
        filtered = await self.filter_commands(group.commands, sort=True)
        
        # Ajouter chaque sous-commande
        for command in filtered:
            signature = self.get_command_signature(command).replace(group.name + " ", "")
            value = command.help or "Aucune description disponible."
            if len(value) > 100:
                value = value[:97] + "..."
            embed.add_field(name=f"{command.name} - `{signature}`", value=value, inline=False)
        
        embed.set_footer(text="Le Séminaire | Bot de communauté artistique")
        
        await self.get_destination().send(embed=embed)
    
    async def send_cog_help(self, cog):
        """
        Affiche l'aide pour un cog (catégorie de commandes).
        """
        # Renommer certaines catégories pour plus de clarté
        display_names = {
            "ResourceCog": "📚 Ressources",
            "MusicCog": "🎵 Musique",
            "CollaborationCog": "🤝 Collaborations",
            "ModerationCog": "🛡️ Modération"
        }
        
        display_name = display_names.get(cog.qualified_name, cog.qualified_name)
        
        embed = discord.Embed(
            title=f"Catégorie: {display_name}",
            color=0x7289da
        )
        
        # Ajouter la description du cog
        if cog.description:
            embed.description = cog.description
        else:
            embed.description = "Collection de commandes pour cette catégorie."
        
        # Filtrer et trier les commandes de ce cog
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        
        # Ajouter chaque commande
        for command in filtered:
            signature = self.get_command_signature(command)
            brief = command.brief or command.help
            if brief:
                if len(brief) > 100:
                    brief = brief[:97] + "..."
            else:
                brief = "Aucune description disponible."
            embed.add_field(name=f"{command.name} - `{signature}`", value=brief, inline=False)
        
        embed.set_footer(text="Le Séminaire | Bot de communauté artistique")
        
        await self.get_destination().send(embed=embed)

async def create_info_embed(ctx):
    """
    Crée un embed avec des informations sur le bot.
    """
    bot = ctx.bot
    embed = discord.Embed(
        title="ℹ️ À propos de LeSéminaire[BOT]",
        description=(
            "Ce bot est conçu spécifiquement pour la communauté artistique du Séminaire, "
            "offrant des outils de collaboration et de partage pour les artistes."
        ),
        color=0x7289da
    )
    
    # Informations générales
    embed.add_field(
        name="📊 Statistiques",
        value=(
            f"**Serveurs:** {len(bot.guilds)}\n"
            f"**Utilisateurs:** {sum(g.member_count for g in bot.guilds)}\n"
            f"**Commandes:** {len(list(bot.walk_commands()))}\n"
            f"**Latence:** {round(bot.latency * 1000)}ms"
        ),
        inline=True
    )
    
    # Fonctionnalités principales
    embed.add_field(
        name="🔧 Fonctionnalités principales",
        value=(
            "• Gestion des ressources artistiques\n"
            "• Lecture musicale et partage de samples\n"
            "• Collaborations entre artistes\n"
            "• Modération et vérification automatiques\n"
            "• Cartes de bienvenue personnalisées"
        ),
        inline=True
    )
    
    # Liens utiles
    embed.add_field(
        name="🔗 Liens utiles",
        value=(
            "[Site du Séminaire](https://leseminaire.art)\n"
            "[Documentation](https://docs.leseminaire.art)\n"
            "[Support](https://discord.gg/leseminaire)"
        ),
        inline=False
    )
    
    embed.set_footer(text="Développé avec ❤️ pour la communauté du Séminaire")
    
    return embed