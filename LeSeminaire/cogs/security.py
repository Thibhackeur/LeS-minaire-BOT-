"""
Module de sécurité pour LeSéminaire[BOT].
Protège le serveur contre les spams, les raids et autres attaques.
"""
import discord
from discord.ext import commands, tasks
import datetime
import asyncio
import re
import logging
from collections import defaultdict, Counter
import typing

# Configuration des niveaux de sécurité
SECURITY_LEVELS = {
    "low": {
        "message_rate": 10,  # messages par 10 secondes
        "mention_limit": 5,  # mentions par message
        "raid_threshold": 7,  # nouveaux membres en 30 secondes
        "similar_threshold": 0.85,  # similarité des messages (0.0 à 1.0)
        "url_limit": 3,  # URLs par message
        "emoji_limit": 10,  # Emojis par message
        "action": "warn"  # avertir seulement
    },
    "medium": {
        "message_rate": 7,
        "mention_limit": 4,
        "raid_threshold": 5,
        "similar_threshold": 0.75,
        "url_limit": 2,
        "emoji_limit": 8,
        "action": "mute"  # muter temporairement
    },
    "high": {
        "message_rate": 5,
        "mention_limit": 3,
        "raid_threshold": 3,
        "similar_threshold": 0.65,
        "url_limit": 1,
        "emoji_limit": 5,
        "action": "kick"  # expulser
    },
    "extreme": {
        "message_rate": 3,
        "mention_limit": 2,
        "raid_threshold": 2,
        "similar_threshold": 0.50,
        "url_limit": 0,
        "emoji_limit": 3,
        "action": "ban"  # bannir
    }
}

# Durée des actions temporaires (en secondes)
TEMP_ACTION_DURATION = {
    "mute": 900,  # 15 minutes
    "ban": 86400  # 24 heures
}

class Security(commands.Cog):
    """Système de sécurité et protection contre le spam/raids pour le bot LeSéminaire."""
    
    def __init__(self, bot):
        self.bot = bot
        self.message_history = defaultdict(list)  # {user_id: [message1, message2, ...]}
        self.join_history = []  # Liste de tuples (member, timestamp)
        self.temp_bans = {}  # {guild_id: {user_id: unban_time}}
        self.temp_mutes = {}  # {guild_id: {user_id: unmute_time}}
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        self.emoji_pattern = re.compile(r'<a?:[a-zA-Z0-9_]+:\d+>|[\U00010000-\U0010ffff]')
        self.security_level = "medium"  # niveau par défaut
        
        # Démarrer les tâches de surveillance
        self.check_temp_bans.start()
        self.check_temp_mutes.start()
        self.clear_old_data.start()
        
        self.logger = logging.getLogger('security')
        handler = logging.FileHandler(filename='security.log', encoding='utf-8', mode='a')
        self.logger.addHandler(handler)
        
    def cog_unload(self):
        """Nettoyage lors du déchargement du cog."""
        self.check_temp_bans.cancel()
        self.check_temp_mutes.cancel()
        self.clear_old_data.cancel()
    
    @tasks.loop(seconds=60)
    async def check_temp_bans(self):
        """Vérifie les bannissements temporaires et débannit si nécessaire."""
        current_time = datetime.datetime.now().timestamp()
        
        for guild_id, bans in list(self.temp_bans.items()):
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
                
            for user_id, unban_time in list(bans.items()):
                if current_time >= unban_time:
                    try:
                        # Débannir l'utilisateur
                        user = await self.bot.fetch_user(int(user_id))
                        await guild.unban(user, reason="Bannissement temporaire expiré")
                        self.logger.info(f"Utilisateur {user.name}#{user.discriminator} débanni sur {guild.name}")
                        del self.temp_bans[guild_id][user_id]
                    except Exception as e:
                        self.logger.error(f"Erreur lors du débannissement: {e}")
    
    @tasks.loop(seconds=60)
    async def check_temp_mutes(self):
        """Vérifie les mutes temporaires et démute si nécessaire."""
        current_time = datetime.datetime.now().timestamp()
        
        for guild_id, mutes in list(self.temp_mutes.items()):
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
                
            for user_id, unmute_time in list(mutes.items()):
                if current_time >= unmute_time:
                    try:
                        # Trouver le membre
                        member = guild.get_member(int(user_id))
                        if member:
                            # Trouver le rôle "Muted"
                            muted_role = discord.utils.get(guild.roles, name="Muted")
                            if muted_role and muted_role in member.roles:
                                await member.remove_roles(muted_role, reason="Mute temporaire expiré")
                                self.logger.info(f"Utilisateur {member.name}#{member.discriminator} démuté sur {guild.name}")
                        
                        del self.temp_mutes[guild_id][user_id]
                    except Exception as e:
                        self.logger.error(f"Erreur lors du démute: {e}")
    
    @tasks.loop(minutes=30)
    async def clear_old_data(self):
        """Nettoie les anciennes données pour préserver la mémoire."""
        # Nettoyer l'historique des messages (garder seulement les 10 dernières minutes)
        cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=10)
        
        for user_id, messages in list(self.message_history.items()):
            # Filtrer les messages récents
            recent_messages = [msg for msg in messages if msg["timestamp"] > cutoff_time]
            if recent_messages:
                self.message_history[user_id] = recent_messages
            else:
                del self.message_history[user_id]
        
        # Nettoyer l'historique des arrivées (garder seulement les 30 dernières minutes)
        cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=30)
        self.join_history = [entry for entry in self.join_history if entry[1] > cutoff_time]
    
    @check_temp_bans.before_loop
    @check_temp_mutes.before_loop
    @clear_old_data.before_loop
    async def before_task(self):
        """Attendre que le bot soit prêt avant de démarrer les tâches."""
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Gestion des messages pour détecter le spam et les comportements abusifs."""
        # Ignorer les messages du bot et des DM
        if message.author.bot or not message.guild:
            return
        
        # Récupérer les paramètres de sécurité actuels
        security_config = SECURITY_LEVELS[self.security_level]
        
        # Stocker le message dans l'historique
        user_id = str(message.author.id)
        self.message_history[user_id].append({
            "content": message.content,
            "timestamp": datetime.datetime.now(),
            "channel_id": message.channel.id
        })
        
        # Vérifier la fréquence des messages
        if await self._check_message_rate(message.author, security_config):
            return  # L'action a déjà été prise
        
        # Vérifier le nombre de mentions
        if await self._check_mention_spam(message, security_config):
            return  # L'action a déjà été prise
        
        # Vérifier les URLs
        if await self._check_url_spam(message, security_config):
            return  # L'action a déjà été prise
        
        # Vérifier les emojis
        if await self._check_emoji_spam(message, security_config):
            return  # L'action a déjà été prise
        
        # Vérifier les messages similaires (spam)
        await self._check_similar_messages(message, security_config)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Détection des raids (plusieurs arrivées en peu de temps)."""
        # Ignorer les bots
        if member.bot:
            return
        
        # Enregistrer l'arrivée
        self.join_history.append((member, datetime.datetime.now()))
        
        # Vérifier s'il y a un raid en cours
        await self._check_raid(member.guild)
    
    async def _check_message_rate(self, member, security_config):
        """Vérifie si un utilisateur envoie trop de messages trop rapidement."""
        user_id = str(member.id)
        
        # Obtenir les messages des 10 dernières secondes
        cutoff_time = datetime.datetime.now() - datetime.timedelta(seconds=10)
        recent_messages = [msg for msg in self.message_history[user_id] 
                          if msg["timestamp"] > cutoff_time]
        
        # Vérifier si le nombre dépasse la limite
        if len(recent_messages) > security_config["message_rate"]:
            reason = f"Spam détecté: {len(recent_messages)} messages en 10 secondes"
            await self._take_action(member, security_config["action"], reason)
            return True
        
        return False
    
    async def _check_mention_spam(self, message, security_config):
        """Vérifie le nombre de mentions dans un message."""
        # Compter les mentions
        mention_count = len(message.mentions) + len(message.role_mentions) + len(message.channel_mentions)
        
        if mention_count > security_config["mention_limit"]:
            reason = f"Spam de mentions détecté: {mention_count} mentions dans un message"
            await self._take_action(message.author, security_config["action"], reason)
            await message.delete()
            return True
        
        return False
    
    async def _check_url_spam(self, message, security_config):
        """Vérifie le nombre d'URLs dans un message."""
        # Trouver toutes les URLs
        urls = self.url_pattern.findall(message.content)
        
        if len(urls) > security_config["url_limit"]:
            reason = f"Spam d'URLs détecté: {len(urls)} URLs dans un message"
            await self._take_action(message.author, security_config["action"], reason)
            await message.delete()
            return True
        
        return False
    
    async def _check_emoji_spam(self, message, security_config):
        """Vérifie le nombre d'emojis dans un message."""
        # Trouver tous les emojis
        emojis = self.emoji_pattern.findall(message.content)
        
        if len(emojis) > security_config["emoji_limit"]:
            reason = f"Spam d'emojis détecté: {len(emojis)} emojis dans un message"
            await self._take_action(message.author, security_config["action"], reason)
            await message.delete()
            return True
        
        return False
    
    async def _check_similar_messages(self, message, security_config):
        """Vérifie si l'utilisateur envoie des messages similaires (spam)."""
        user_id = str(message.author.id)
        
        # Obtenir les messages récents de l'utilisateur
        recent_messages = self.message_history[user_id][-5:]  # Derniers 5 messages
        
        if len(recent_messages) < 3:
            return False  # Pas assez de messages pour comparer
        
        # Vérifier la similarité entre les messages récents
        current_content = message.content.lower()
        similar_count = 0
        
        for msg in recent_messages[:-1]:  # Ignorer le message actuel
            old_content = msg["content"].lower()
            
            # Calculer la similarité (méthode simple)
            similarity = self._calculate_similarity(current_content, old_content)
            
            if similarity > security_config["similar_threshold"]:
                similar_count += 1
        
        if similar_count >= 2:  # Au moins 2 messages similaires récents
            reason = "Spam détecté: messages similaires répétés"
            await self._take_action(message.author, security_config["action"], reason)
            await message.delete()
            return True
        
        return False
    
    async def _check_raid(self, guild):
        """Vérifie s'il y a un raid en cours (plusieurs arrivées rapprochées)."""
        # Obtenir les arrivées des 30 dernières secondes
        cutoff_time = datetime.datetime.now() - datetime.timedelta(seconds=30)
        recent_joins = [entry for entry in self.join_history if entry[1] > cutoff_time]
        
        # Récupérer les paramètres de sécurité actuels
        security_config = SECURITY_LEVELS[self.security_level]
        
        # Vérifier si le nombre dépasse le seuil
        if len(recent_joins) >= security_config["raid_threshold"]:
            # Activer le mode verrouillage
            await self._enable_raid_mode(guild)
    
    async def _enable_raid_mode(self, guild):
        """Active le mode anti-raid (verrouille temporairement le serveur)."""
        # Rechercher les canaux publics
        public_channels = [channel for channel in guild.text_channels 
                          if channel.permissions_for(guild.default_role).read_messages]
        
        # Trouver le rôle everyone
        everyone_role = guild.default_role
        
        # Log l'activation du mode raid
        self.logger.warning(f"Mode anti-raid activé sur {guild.name} - Verrouillage des canaux en cours")
        
        # Annoncer dans le canal système si disponible
        system_channel = guild.system_channel
        if system_channel:
            embed = discord.Embed(
                title="⚠️ Alerte de Sécurité",
                description="Mode anti-raid activé! Trop d'utilisateurs ont rejoint en peu de temps.",
                color=discord.Color.red()
            )
            embed.add_field(name="Action", value="Canaux temporairement verrouillés")
            embed.set_footer(text="La situation sera analysée par la modération")
            
            try:
                await system_channel.send(embed=embed)
            except:
                pass
        
        # Verrouiller tous les canaux publics pour le rôle everyone
        for channel in public_channels:
            try:
                # Sauvegarder les permissions actuelles et désactiver l'envoi de messages
                overwrite = channel.overwrites_for(everyone_role)
                overwrite.send_messages = False
                await channel.set_permissions(everyone_role, overwrite=overwrite)
            except Exception as e:
                self.logger.error(f"Erreur lors du verrouillage du canal {channel.name}: {e}")
        
        # Planifier le déverrouillage après 5 minutes
        await asyncio.sleep(300)  # 5 minutes
        
        # Déverrouiller les canaux
        for channel in public_channels:
            try:
                overwrite = channel.overwrites_for(everyone_role)
                overwrite.send_messages = None  # Réinitialiser à la valeur par défaut
                await channel.set_permissions(everyone_role, overwrite=overwrite)
            except Exception as e:
                self.logger.error(f"Erreur lors du déverrouillage du canal {channel.name}: {e}")
        
        # Log la fin du mode raid
        self.logger.info(f"Mode anti-raid désactivé sur {guild.name} - Canaux déverrouillés")
        
        # Annoncer la fin du mode raid
        if system_channel:
            embed = discord.Embed(
                title="✅ Sécurité Restaurée",
                description="Mode anti-raid désactivé. Les canaux sont de nouveau accessibles.",
                color=discord.Color.green()
            )
            
            try:
                await system_channel.send(embed=embed)
            except:
                pass
    
    async def _take_action(self, member, action_type, reason):
        """Applique l'action de modération appropriée sur un membre."""
        guild = member.guild
        
        # Log l'action
        self.logger.warning(f"Action de sécurité: {action_type} pour {member.name}#{member.discriminator} dans {guild.name}. Raison: {reason}")
        
        try:
            # Exécuter l'action en fonction du type
            if action_type == "warn":
                # Envoyer un avertissement dans un canal de modération
                log_channel = discord.utils.get(guild.text_channels, name="bot-logs") or guild.system_channel
                if log_channel:
                    embed = discord.Embed(
                        title="⚠️ Avertissement Automatique",
                        description=f"Utilisateur: {member.mention}\nRaison: {reason}",
                        color=discord.Color.gold()
                    )
                    await log_channel.send(embed=embed)
                
                # Avertir l'utilisateur
                try:
                    await member.send(f"⚠️ **Avertissement** - Vous avez déclenché notre système anti-spam sur *{guild.name}*.\nRaison: {reason}\n\nVeuillez respecter les règles du serveur pour éviter des sanctions plus sévères.")
                except:
                    # Impossible d'envoyer un DM
                    pass
                    
            elif action_type == "mute":
                # Trouver ou créer un rôle "Muted"
                muted_role = discord.utils.get(guild.roles, name="Muted")
                if not muted_role:
                    # Créer le rôle s'il n'existe pas
                    try:
                        muted_role = await guild.create_role(name="Muted", reason="Création du rôle pour le système anti-spam")
                        
                        # Configurer les permissions du rôle pour tous les canaux
                        for channel in guild.channels:
                            await channel.set_permissions(muted_role, send_messages=False, speak=False)
                    except Exception as e:
                        self.logger.error(f"Erreur lors de la création du rôle Muted: {e}")
                        return
                
                # Appliquer le rôle
                await member.add_roles(muted_role, reason=reason)
                
                # Enregistrer le mute temporaire
                guild_id = str(guild.id)
                user_id = str(member.id)
                
                if guild_id not in self.temp_mutes:
                    self.temp_mutes[guild_id] = {}
                
                unmute_time = datetime.datetime.now().timestamp() + TEMP_ACTION_DURATION["mute"]
                self.temp_mutes[guild_id][user_id] = unmute_time
                
                # Notifier l'utilisateur
                try:
                    duration_minutes = TEMP_ACTION_DURATION["mute"] // 60
                    await member.send(f"🔇 **Mute Temporaire** - Vous avez été réduit au silence sur *{guild.name}* pendant {duration_minutes} minutes.\nRaison: {reason}")
                except:
                    pass
                
                # Log dans un canal de modération
                log_channel = discord.utils.get(guild.text_channels, name="bot-logs") or guild.system_channel
                if log_channel:
                    embed = discord.Embed(
                        title="🔇 Utilisateur Réduit au Silence",
                        description=f"Utilisateur: {member.mention}\nRaison: {reason}\nDurée: {duration_minutes} minutes",
                        color=discord.Color.orange()
                    )
                    await log_channel.send(embed=embed)
                    
            elif action_type == "kick":
                # Expulser l'utilisateur
                await member.kick(reason=reason)
                
                # Log dans un canal de modération
                log_channel = discord.utils.get(guild.text_channels, name="bot-logs") or guild.system_channel
                if log_channel:
                    embed = discord.Embed(
                        title="👢 Utilisateur Expulsé",
                        description=f"Utilisateur: {member.name}#{member.discriminator}\nRaison: {reason}",
                        color=discord.Color.dark_orange()
                    )
                    await log_channel.send(embed=embed)
                
            elif action_type == "ban":
                # Bannir l'utilisateur
                await member.ban(reason=reason, delete_message_days=1)
                
                # Enregistrer le bannissement temporaire
                guild_id = str(guild.id)
                user_id = str(member.id)
                
                if guild_id not in self.temp_bans:
                    self.temp_bans[guild_id] = {}
                
                unban_time = datetime.datetime.now().timestamp() + TEMP_ACTION_DURATION["ban"]
                self.temp_bans[guild_id][user_id] = unban_time
                
                # Log dans un canal de modération
                log_channel = discord.utils.get(guild.text_channels, name="bot-logs") or guild.system_channel
                if log_channel:
                    duration_hours = TEMP_ACTION_DURATION["ban"] // 3600
                    embed = discord.Embed(
                        title="🔨 Utilisateur Banni Temporairement",
                        description=f"Utilisateur: {member.name}#{member.discriminator}\nRaison: {reason}\nDurée: {duration_hours} heures",
                        color=discord.Color.red()
                    )
                    await log_channel.send(embed=embed)
        
        except Exception as e:
            self.logger.error(f"Erreur lors de l'application de l'action {action_type}: {e}")
    
    def _calculate_similarity(self, str1, str2):
        """Calcule la similarité entre deux chaînes (0.0 à 1.0)."""
        # Version simple de la similarité
        if str1 == str2:
            return 1.0
        
        # Compter les caractères communs
        if not str1 or not str2:
            return 0.0
            
        # Compter les bigrammes communs
        def get_bigrams(s):
            return [s[i:i+2] for i in range(len(s)-1)]
            
        bigrams1 = get_bigrams(str1)
        bigrams2 = get_bigrams(str2)
        
        if not bigrams1 or not bigrams2:
            return 0.0
            
        intersection = len(set(bigrams1) & set(bigrams2))
        union = len(set(bigrams1) | set(bigrams2))
        
        return intersection / union
    
    @commands.group(name="security", aliases=["sécu", "securite"])
    @commands.has_permissions(administrator=True)
    async def security_cmd(self, ctx):
        """Gestion des paramètres de sécurité du bot."""
        if ctx.invoked_subcommand is None:
            await self._show_security_status(ctx)
    
    @security_cmd.command(name="level", aliases=["niveau"])
    async def security_level_cmd(self, ctx, level: str):
        """Définit le niveau de sécurité du bot (low, medium, high, extreme)."""
        if level.lower() not in SECURITY_LEVELS:
            await ctx.send(f"❌ Niveau de sécurité invalide. Choisissez parmi: {', '.join(SECURITY_LEVELS.keys())}")
            return
        
        self.security_level = level.lower()
        
        # Créer un embed pour montrer les paramètres du niveau choisi
        config = SECURITY_LEVELS[self.security_level]
        
        embed = discord.Embed(
            title=f"🛡️ Niveau de Sécurité: {self.security_level.upper()}",
            description="Les paramètres de sécurité ont été mis à jour.",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Limite de messages", value=f"{config['message_rate']} messages / 10s", inline=True)
        embed.add_field(name="Limite de mentions", value=f"{config['mention_limit']} mentions", inline=True)
        embed.add_field(name="Seuil de raid", value=f"{config['raid_threshold']} joins / 30s", inline=True)
        embed.add_field(name="Limite d'URLs", value=f"{config['url_limit']} URLs", inline=True)
        embed.add_field(name="Limite d'emojis", value=f"{config['emoji_limit']} emojis", inline=True)
        embed.add_field(name="Action automatique", value=f"{config['action']}", inline=True)
        
        await ctx.send(embed=embed)
        
        # Log le changement
        self.logger.info(f"Niveau de sécurité modifié à {self.security_level} par {ctx.author.name}#{ctx.author.discriminator}")
    
    @security_cmd.command(name="status", aliases=["statut", "état", "etat"])
    async def security_status_cmd(self, ctx):
        """Affiche le statut actuel et les paramètres de sécurité."""
        await self._show_security_status(ctx)
    
    async def _show_security_status(self, ctx):
        """Affiche les informations sur la configuration de sécurité actuelle."""
        config = SECURITY_LEVELS[self.security_level]
        
        embed = discord.Embed(
            title="🛡️ Statut du Système de Sécurité",
            description=f"**Niveau actuel**: {self.security_level.upper()}",
            color=discord.Color.blue()
        )
        
        # Statistiques
        embed.add_field(name="Utilisateurs surveillés", value=f"{len(self.message_history)}", inline=True)
        embed.add_field(name="Mutes temporaires", value=f"{sum(len(mutes) for mutes in self.temp_mutes.values())}", inline=True)
        embed.add_field(name="Bans temporaires", value=f"{sum(len(bans) for bans in self.temp_bans.values())}", inline=True)
        
        # Paramètres actuels
        embed.add_field(name="Paramètres de Protection", value="\u200b", inline=False)
        embed.add_field(name="Limite de messages", value=f"{config['message_rate']} messages / 10s", inline=True)
        embed.add_field(name="Limite de mentions", value=f"{config['mention_limit']} mentions", inline=True)
        embed.add_field(name="Seuil de raid", value=f"{config['raid_threshold']} joins / 30s", inline=True)
        embed.add_field(name="Limite d'URLs", value=f"{config['url_limit']} URLs", inline=True)
        embed.add_field(name="Limite d'emojis", value=f"{config['emoji_limit']} emojis", inline=True)
        embed.add_field(name="Action automatique", value=f"{config['action']}", inline=True)
        
        await ctx.send(embed=embed)
    
    @security_cmd.command(name="unmute", aliases=["démute", "demute"])
    async def security_unmute_cmd(self, ctx, member: discord.Member):
        """Démute manuellement un utilisateur."""
        # Trouver le rôle "Muted"
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            await ctx.send("❌ Le rôle 'Muted' n'existe pas sur ce serveur.")
            return
        
        # Vérifier si l'utilisateur est mute
        if muted_role not in member.roles:
            await ctx.send(f"❌ {member.mention} n'est pas actuellement réduit au silence.")
            return
        
        # Retirer le rôle
        await member.remove_roles(muted_role, reason=f"Démute manuel par {ctx.author}")
        
        # Supprimer de la liste des mutes temporaires
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        
        if guild_id in self.temp_mutes and user_id in self.temp_mutes[guild_id]:
            del self.temp_mutes[guild_id][user_id]
        
        await ctx.send(f"✅ {member.mention} a été démuté avec succès.")
        
        # Log l'action
        self.logger.info(f"{member.name}#{member.discriminator} a été démuté par {ctx.author.name}#{ctx.author.discriminator}")

async def setup(bot):
    """Ajoute le cog de sécurité au bot."""
    await bot.add_cog(Security(bot))