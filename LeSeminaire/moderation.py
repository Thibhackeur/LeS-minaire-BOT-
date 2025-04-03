"""
Module de commandes de modération pour le bot Le Séminaire.
Fournit des outils pour la gestion et la modération du serveur.
"""

import discord
from discord.ext import commands
import asyncio
import logging
from typing import Optional, Union, List

# Configuration du logger
logger = logging.getLogger('moderation')

class Moderation:
    """
    Classe de gestion des commandes de modération.
    """
    
    def __init__(self, bot):
        """
        Initialise le module de modération.
        
        Args:
            bot: L'instance du bot Discord
        """
        self.bot = bot
        self.muted_users = {}  # user_id -> expiration_time
    
    async def setup_mute_role(self, guild: discord.Guild) -> discord.Role:
        """
        Configure le rôle "Muet" s'il n'existe pas.
        
        Args:
            guild: Le serveur Discord
            
        Returns:
            Le rôle "Muet"
        """
        mute_role = discord.utils.get(guild.roles, name="Muet")
        
        if not mute_role:
            # Créer le rôle
            mute_role = await guild.create_role(
                name="Muet",
                color=discord.Color.dark_gray(),
                reason="Création du rôle Muet pour la modération"
            )
            
            # Configurer les permissions (pas de droits d'envoi de messages)
            for channel in guild.channels:
                try:
                    await channel.set_permissions(
                        mute_role,
                        send_messages=False,
                        add_reactions=False,
                        speak=False,
                        stream=False,
                        reason="Configuration des permissions du rôle Muet"
                    )
                except Exception as e:
                    logger.error(f"Erreur lors de la configuration des permissions pour le canal {channel.name}: {e}")
            
            logger.info(f"Rôle Muet créé sur le serveur {guild.name}")
        
        return mute_role
    
    async def mute_user(self, ctx: commands.Context, member: discord.Member, duration: int, reason: str) -> bool:
        """
        Rend un membre muet pour une durée spécifiée.
        
        Args:
            ctx: Le contexte de la commande
            member: Le membre à rendre muet
            duration: La durée du mute en minutes
            reason: La raison du mute
            
        Returns:
            True si le mute a réussi, False sinon
        """
        try:
            # Vérifier si l'utilisateur est modérable
            if not member.guild.me.top_role > member.top_role:
                await ctx.send(f"❌ Je ne peux pas rendre {member.mention} muet car son rôle est supérieur au mien.")
                return False
            
            # Configurer le rôle muet
            mute_role = await self.setup_mute_role(ctx.guild)
            
            # Appliquer le rôle
            await member.add_roles(mute_role, reason=f"Mute par {ctx.author.name} - Raison: {reason}")
            
            # Enregistrer le mute
            expiration = asyncio.get_event_loop().time() + (duration * 60)
            self.muted_users[member.id] = expiration
            
            # Planifier l'unmute
            self.bot.loop.create_task(self._schedule_unmute(member, duration))
            
            # Logger l'action
            logger.info(f"Membre {member.name} rendu muet par {ctx.author.name} pour {duration} minutes. Raison: {reason}")
            
            # Informer l'utilisateur
            try:
                await member.send(
                    f"Tu as été rendu muet sur le serveur **{ctx.guild.name}** pour **{duration}** minutes.\n"
                    f"Raison: {reason}\n\n"
                    f"Tu pourras à nouveau parler après cette période."
                )
            except:
                logger.warning(f"Impossible d'envoyer un MP à {member.name} concernant son mute")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du mute de {member.name}: {e}")
            await ctx.send(f"❌ Une erreur s'est produite: {e}")
            return False
    
    async def _schedule_unmute(self, member: discord.Member, duration: int):
        """
        Planifie la fin du mute d'un membre.
        
        Args:
            member: Le membre à démuter
            duration: La durée du mute en minutes
        """
        await asyncio.sleep(duration * 60)
        
        # Vérifier si le membre est toujours sur le serveur
        if member.guild.get_member(member.id):
            try:
                # Vérifier si le membre est toujours enregistré comme muet
                if member.id in self.muted_users:
                    # Retirer le rôle muet
                    mute_role = discord.utils.get(member.guild.roles, name="Muet")
                    
                    if mute_role and mute_role in member.roles:
                        await member.remove_roles(mute_role, reason="Fin de la période de mute")
                        
                        # Informer l'utilisateur
                        try:
                            await member.send(
                                f"Tu n'es plus muet sur le serveur **{member.guild.name}**.\n"
                                f"Tu peux à nouveau participer aux discussions."
                            )
                        except:
                            pass
                        
                        logger.info(f"Membre {member.name} démute automatiquement après {duration} minutes.")
                    
                    # Supprimer l'enregistrement
                    del self.muted_users[member.id]
            
            except Exception as e:
                logger.error(f"Erreur lors du démute automatique de {member.name}: {e}")
    
    async def unmute_user(self, ctx: commands.Context, member: discord.Member, reason: str) -> bool:
        """
        Retire le statut muet d'un membre.
        
        Args:
            ctx: Le contexte de la commande
            member: Le membre à démuter
            reason: La raison du démute
            
        Returns:
            True si le démute a réussi, False sinon
        """
        try:
            mute_role = discord.utils.get(ctx.guild.roles, name="Muet")
            
            if not mute_role:
                await ctx.send("❌ Le rôle Muet n'existe pas sur ce serveur.")
                return False
            
            if mute_role not in member.roles:
                await ctx.send(f"❌ {member.mention} n'est pas muet.")
                return False
            
            # Retirer le rôle
            await member.remove_roles(mute_role, reason=f"Démute par {ctx.author.name} - Raison: {reason}")
            
            # Supprimer l'enregistrement si présent
            if member.id in self.muted_users:
                del self.muted_users[member.id]
            
            # Logger l'action
            logger.info(f"Membre {member.name} démute par {ctx.author.name}. Raison: {reason}")
            
            # Informer l'utilisateur
            try:
                await member.send(
                    f"Tu n'es plus muet sur le serveur **{ctx.guild.name}**.\n"
                    f"Raison: {reason}\n\n"
                    f"Tu peux à nouveau participer aux discussions."
                )
            except:
                logger.warning(f"Impossible d'envoyer un MP à {member.name} concernant son démute")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du démute de {member.name}: {e}")
            await ctx.send(f"❌ Une erreur s'est produite: {e}")
            return False
    
    async def kick_user(self, ctx: commands.Context, member: discord.Member, reason: str) -> bool:
        """
        Expulse un membre du serveur.
        
        Args:
            ctx: Le contexte de la commande
            member: Le membre à expulser
            reason: La raison de l'expulsion
            
        Returns:
            True si l'expulsion a réussi, False sinon
        """
        try:
            # Vérifier si l'utilisateur est modérable
            if not member.guild.me.top_role > member.top_role:
                await ctx.send(f"❌ Je ne peux pas expulser {member.mention} car son rôle est supérieur au mien.")
                return False
            
            # Informer l'utilisateur avant l'expulsion
            try:
                await member.send(
                    f"Tu as été expulsé du serveur **{ctx.guild.name}**.\n"
                    f"Raison: {reason}\n\n"
                    f"Tu peux rejoindre à nouveau le serveur si tu le souhaites."
                )
            except:
                logger.warning(f"Impossible d'envoyer un MP à {member.name} concernant son expulsion")
            
            # Expulser le membre
            await member.kick(reason=f"Expulsé par {ctx.author.name} - Raison: {reason}")
            
            # Logger l'action
            logger.info(f"Membre {member.name} expulsé par {ctx.author.name}. Raison: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'expulsion de {member.name}: {e}")
            await ctx.send(f"❌ Une erreur s'est produite: {e}")
            return False
    
    async def ban_user(self, ctx: commands.Context, member: discord.Member, reason: str, delete_days: int = 0) -> bool:
        """
        Bannit un membre du serveur.
        
        Args:
            ctx: Le contexte de la commande
            member: Le membre à bannir
            reason: La raison du bannissement
            delete_days: Nombre de jours de messages à supprimer
            
        Returns:
            True si le bannissement a réussi, False sinon
        """
        try:
            # Vérifier si l'utilisateur est modérable
            if not member.guild.me.top_role > member.top_role:
                await ctx.send(f"❌ Je ne peux pas bannir {member.mention} car son rôle est supérieur au mien.")
                return False
            
            # Informer l'utilisateur avant le bannissement
            try:
                await member.send(
                    f"Tu as été banni du serveur **{ctx.guild.name}**.\n"
                    f"Raison: {reason}"
                )
            except:
                logger.warning(f"Impossible d'envoyer un MP à {member.name} concernant son bannissement")
            
            # Bannir le membre
            await member.ban(reason=f"Banni par {ctx.author.name} - Raison: {reason}", delete_message_days=delete_days)
            
            # Logger l'action
            logger.info(f"Membre {member.name} banni par {ctx.author.name}. Raison: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du bannissement de {member.name}: {e}")
            await ctx.send(f"❌ Une erreur s'est produite: {e}")
            return False
    
    async def unban_user(self, ctx: commands.Context, user_id: int, reason: str) -> bool:
        """
        Débannit un utilisateur du serveur.
        
        Args:
            ctx: Le contexte de la commande
            user_id: L'ID de l'utilisateur à débannir
            reason: La raison du débannissement
            
        Returns:
            True si le débannissement a réussi, False sinon
        """
        try:
            # Récupérer la liste des bannis
            bans = await ctx.guild.bans()
            
            # Trouver l'utilisateur
            user_to_unban = None
            for ban_entry in bans:
                if ban_entry.user.id == user_id:
                    user_to_unban = ban_entry.user
                    break
            
            if not user_to_unban:
                await ctx.send(f"❌ Aucun utilisateur avec l'ID {user_id} n'est banni.")
                return False
            
            # Débannir l'utilisateur
            await ctx.guild.unban(user_to_unban, reason=f"Débanni par {ctx.author.name} - Raison: {reason}")
            
            # Logger l'action
            logger.info(f"Utilisateur {user_to_unban.name} débanni par {ctx.author.name}. Raison: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du débannissement de l'utilisateur {user_id}: {e}")
            await ctx.send(f"❌ Une erreur s'est produite: {e}")
            return False
    
    async def prune_messages(self, ctx: commands.Context, limit: int, member: Optional[discord.Member] = None) -> int:
        """
        Supprime un nombre défini de messages dans un canal.
        
        Args:
            ctx: Le contexte de la commande
            limit: Nombre de messages à supprimer
            member: Si spécifié, supprime uniquement les messages de ce membre
            
        Returns:
            Nombre de messages supprimés
        """
        try:
            # Vérifier les limites
            if limit <= 0 or limit > 100:
                await ctx.send("❌ Le nombre de messages à supprimer doit être entre 1 et 100.")
                return 0
            
            # Définir le filtre si nécessaire
            check = None
            if member:
                check = lambda m: m.author == member
            
            # Supprimer les messages
            deleted = await ctx.channel.purge(limit=limit, check=check)
            
            # Logger l'action
            logger.info(f"{len(deleted)} messages supprimés par {ctx.author.name} dans le canal {ctx.channel.name}.")
            
            return len(deleted)
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des messages: {e}")
            await ctx.send(f"❌ Une erreur s'est produite: {e}")
            return 0
    
    async def warn_user(self, ctx: commands.Context, member: discord.Member, reason: str) -> bool:
        """
        Donne un avertissement à un membre.
        
        Args:
            ctx: Le contexte de la commande
            member: Le membre à avertir
            reason: La raison de l'avertissement
            
        Returns:
            True si l'avertissement a été envoyé, False sinon
        """
        try:
            # Informer l'utilisateur
            try:
                await member.send(
                    f"Tu as reçu un avertissement sur le serveur **{ctx.guild.name}**.\n"
                    f"Raison: {reason}\n\n"
                    f"Merci de respecter les règles du serveur."
                )
            except:
                logger.warning(f"Impossible d'envoyer un MP à {member.name} concernant son avertissement")
                await ctx.send(f"⚠️ {member.mention} a été averti, mais je n'ai pas pu lui envoyer de message privé.")
                return False
            
            # Logger l'action
            logger.info(f"Membre {member.name} averti par {ctx.author.name}. Raison: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'avertissement de {member.name}: {e}")
            await ctx.send(f"❌ Une erreur s'est produite: {e}")
            return False