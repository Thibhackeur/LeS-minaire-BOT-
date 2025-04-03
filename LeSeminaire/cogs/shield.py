"""
Module de protection (Shield) pour LeSéminaire[BOT].
Fournit une protection avancée contre les attaques DDoS, les bots malveillants et autres menaces.
"""
import discord
from discord.ext import commands, tasks
import datetime
import asyncio
import logging
import json
import os
import re
import typing
from collections import defaultdict, deque

# Configuration des niveaux de protection
SHIELD_LEVELS = {
    "low": {
        "join_rate_limit": 5,  # membres par minute
        "verification_required": False,  # exiger la vérification
        "invite_restriction": False,  # restreindre les invitations
        "new_account_restriction": False,  # restreindre les nouveaux comptes
        "auto_ban_suspicious": False,  # bannir automatiquement les comptes suspects
    },
    "medium": {
        "join_rate_limit": 3,
        "verification_required": True,
        "invite_restriction": False,
        "new_account_restriction": True,  # comptes de moins de 3 jours
        "auto_ban_suspicious": False,
    },
    "high": {
        "join_rate_limit": 2,
        "verification_required": True,
        "invite_restriction": True,
        "new_account_restriction": True,  # comptes de moins de 7 jours
        "auto_ban_suspicious": True,
    },
    "lockdown": {
        "join_rate_limit": 1,
        "verification_required": True,
        "invite_restriction": True,
        "new_account_restriction": True,  # comptes de moins de 14 jours
        "auto_ban_suspicious": True,
    }
}

# Modèles suspects (noms d'utilisateurs, caractéristiques des bots, etc.)
SUSPICIOUS_PATTERNS = [
    r"discord\.gg\/",  # lien d'invitation Discord
    r"[a-zA-Z0-9]{15,}",  # longue chaîne aléatoire
    r"(nitro|free|gift|steam|airdrop)",  # mots-clés de scam
    r".*(h-t-t-p-s|h.t.t.p.s|h_t_t_p_s).*",  # URLs obfusquées
    r"[a-zA-Z0-9]+\.[a-z]{2,6}\/[a-zA-Z0-9]+",  # URL simplifiée
]

class Shield(commands.Cog):
    """Système de protection avancé pour LeSéminaire[BOT]."""
    
    def __init__(self, bot):
        self.bot = bot
        self.shield_level = "medium"  # niveau par défaut
        self.join_history = defaultdict(lambda: deque(maxlen=60))  # {guild_id: deque[(member, timestamp)]}
        self.lockdown_status = {}  # {guild_id: {'active': bool, 'until': timestamp}}
        self.verification_channels = {}  # {guild_id: channel_id}
        self.suspicious_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in SUSPICIOUS_PATTERNS]
        self.trusted_members = set()  # ensemble d'IDs de membres de confiance
        self.action_logs = defaultdict(list)  # {guild_id: [actions]}
        
        # Démarrer les tâches de surveillance
        self.check_lockdowns.start()
        self.scan_guild_members.start()
        
        # Logger
        self.logger = logging.getLogger('shield')
        handler = logging.FileHandler(filename='shield.log', encoding='utf-8', mode='a')
        self.logger.addHandler(handler)
        
        # Charger les données persistantes (si disponibles)
        self._load_data()
    
    def _load_data(self):
        """Charge les données persistantes depuis un fichier."""
        try:
            if os.path.exists('shield_data.json'):
                with open('shield_data.json', 'r') as f:
                    data = json.load(f)
                    
                    if 'shield_level' in data:
                        self.shield_level = data['shield_level']
                    
                    if 'verification_channels' in data:
                        self.verification_channels = data['verification_channels']
                    
                    if 'trusted_members' in data:
                        self.trusted_members = set(data['trusted_members'])
                    
                    if 'lockdown_status' in data:
                        self.lockdown_status = data['lockdown_status']
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement des données du bouclier: {e}")
    
    def _save_data(self):
        """Sauvegarde les données persistantes dans un fichier."""
        try:
            data = {
                'shield_level': self.shield_level,
                'verification_channels': self.verification_channels,
                'trusted_members': list(self.trusted_members),
                'lockdown_status': self.lockdown_status
            }
            
            with open('shield_data.json', 'w') as f:
                json.dump(data, f)
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde des données du bouclier: {e}")
    
    def cog_unload(self):
        """Nettoyage lors du déchargement du cog."""
        self.check_lockdowns.cancel()
        self.scan_guild_members.cancel()
        self._save_data()
    
    @tasks.loop(minutes=5)
    async def check_lockdowns(self):
        """Vérifie les verrouillages actifs et les désactive si nécessaire."""
        current_time = datetime.datetime.now().timestamp()
        
        for guild_id, status in list(self.lockdown_status.items()):
            if status.get('active', False) and status.get('until', 0) < current_time:
                # Le verrouillage est expiré, le désactiver
                await self._disable_lockdown(guild_id)
    
    @tasks.loop(minutes=15)
    async def scan_guild_members(self):
        """Analyse périodique des membres du serveur pour détecter les comptes suspects."""
        config = SHIELD_LEVELS[self.shield_level]
        
        if not config['auto_ban_suspicious']:
            return  # Ne pas scanner si la fonctionnalité est désactivée
        
        for guild in self.bot.guilds:
            suspicious_members = []
            
            # Analyser les membres pour détecter les motifs suspects
            for member in guild.members:
                if await self._is_suspicious(member) and not self._is_trusted(member):
                    suspicious_members.append(member)
            
            if suspicious_members:
                # Alerter dans le canal système
                system_channel = guild.system_channel
                if system_channel:
                    embed = discord.Embed(
                        title="🛡️ Alerte de Sécurité",
                        description=f"Le scan de sécurité a détecté {len(suspicious_members)} compte(s) suspect(s).",
                        color=discord.Color.red()
                    )
                    
                    for i, member in enumerate(suspicious_members[:5]):  # Limiter à 5 pour éviter des embeds trop grands
                        embed.add_field(
                            name=f"Compte Suspect #{i+1}",
                            value=f"**Utilisateur**: {member.mention}\n**Créé le**: {member.created_at.strftime('%d/%m/%Y')}\n**Rejoint le**: {member.joined_at.strftime('%d/%m/%Y') if member.joined_at else 'Inconnu'}",
                            inline=False
                        )
                    
                    if len(suspicious_members) > 5:
                        embed.add_field(
                            name="Note",
                            value=f"Et {len(suspicious_members) - 5} autre(s) compte(s) suspect(s)...",
                            inline=False
                        )
                    
                    await system_channel.send(embed=embed)
                
                # Enregistrer dans les logs
                self.logger.warning(f"Comptes suspects détectés sur {guild.name}: {', '.join([f'{m.name}#{m.discriminator}' for m in suspicious_members])}")
    
    @check_lockdowns.before_loop
    @scan_guild_members.before_loop
    async def before_task(self):
        """Attendre que le bot soit prêt avant de démarrer les tâches."""
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Gestion des nouveaux arrivants selon le niveau de protection."""
        # Ignorer les bots (ils sont déjà vérifiés par l'API Discord)
        if member.bot:
            return
        
        guild = member.guild
        guild_id = str(guild.id)
        
        # Enregistrer l'arrivée
        self.join_history[guild_id].append((member, datetime.datetime.now()))
        
        # Récupérer les paramètres de protection
        config = SHIELD_LEVELS[self.shield_level]
        
        # Vérifier le taux d'arrivées
        await self._check_join_rate(guild)
        
        # Si le serveur est en mode verrouillage, expulser immédiatement
        if self._is_lockdown_active(guild_id):
            try:
                await member.send(f"⚠️ Le serveur **{guild.name}** est actuellement en mode verrouillage et n'accepte pas de nouveaux membres. Veuillez réessayer plus tard.")
            except:
                pass
            
            try:
                await member.kick(reason="Serveur en mode verrouillage")
                self.logger.info(f"Membre {member.name}#{member.discriminator} expulsé: serveur en mode verrouillage")
                return
            except Exception as e:
                self.logger.error(f"Erreur lors de l'expulsion en mode verrouillage: {e}")
        
        # Vérifier si le compte est trop récent
        if config['new_account_restriction']:
            account_age = (datetime.datetime.now() - member.created_at).days
            min_age = 3 if self.shield_level == "medium" else (7 if self.shield_level == "high" else 14)
            
            if account_age < min_age:
                try:
                    await member.send(f"⚠️ Votre compte Discord est trop récent pour rejoindre **{guild.name}**.\nLes comptes doivent avoir au moins {min_age} jours pour des raisons de sécurité.")
                except:
                    pass
                
                try:
                    await member.kick(reason=f"Compte trop récent ({account_age} jours)")
                    self.logger.info(f"Membre {member.name}#{member.discriminator} expulsé: compte trop récent ({account_age} jours)")
                    return
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'expulsion pour compte récent: {e}")
        
        # Vérifier si le compte est suspect
        if config['auto_ban_suspicious'] and await self._is_suspicious(member):
            try:
                await member.send(f"⚠️ Vous avez été banni de **{guild.name}** car votre compte a été identifié comme suspect par notre système de sécurité.")
            except:
                pass
            
            try:
                await member.ban(reason="Compte suspect")
                self.logger.info(f"Membre {member.name}#{member.discriminator} banni: compte suspect")
                return
            except Exception as e:
                self.logger.error(f"Erreur lors du bannissement pour compte suspect: {e}")
        
        # Si la vérification est requise, envoyer un message dans le canal approprié
        if config['verification_required'] and guild_id in self.verification_channels:
            verification_channel_id = self.verification_channels[guild_id]
            verification_channel = guild.get_channel(int(verification_channel_id))
            
            if verification_channel:
                # Rôle non vérifié
                unverified_role = discord.utils.get(guild.roles, name="Non Vérifié")
                if unverified_role:
                    try:
                        await member.add_roles(unverified_role)
                    except Exception as e:
                        self.logger.error(f"Erreur lors de l'attribution du rôle Non Vérifié: {e}")
                
                # Message de vérification
                embed = discord.Embed(
                    title="🔐 Vérification Requise",
                    description=f"Bienvenue {member.mention} sur **{guild.name}**!\n\nPour accéder au serveur, veuillez compléter la vérification en réagissant à ce message avec ✅.",
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Cette vérification est une mesure de sécurité contre les bots et les raids.")
                
                try:
                    verify_msg = await verification_channel.send(embed=embed)
                    await verify_msg.add_reaction("✅")
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'envoi du message de vérification: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Analyse les messages pour détecter les contenus malveillants."""
        # Ignorer les messages du bot et des DM
        if message.author.bot or not message.guild:
            return
        
        # Ignorer les membres de confiance
        if self._is_trusted(message.author):
            return
        
        # Vérifier les contenus malveillants
        if await self._contains_malicious_content(message):
            # Supprimer le message
            try:
                await message.delete()
            except Exception as e:
                self.logger.error(f"Erreur lors de la suppression du message malveillant: {e}")
                return
            
            # Avertir ou prendre des mesures selon le niveau de protection
            config = SHIELD_LEVELS[self.shield_level]
            
            if config['auto_ban_suspicious']:
                try:
                    await message.author.ban(reason="Contenu malveillant détecté", delete_message_days=1)
                    self.logger.warning(f"Utilisateur {message.author.name}#{message.author.discriminator} banni pour contenu malveillant")
                except Exception as e:
                    self.logger.error(f"Erreur lors du bannissement pour contenu malveillant: {e}")
            else:
                # Log dans un canal approprié
                log_channel = discord.utils.get(message.guild.text_channels, name="bot-logs") or message.guild.system_channel
                if log_channel:
                    embed = discord.Embed(
                        title="⚠️ Contenu Malveillant Détecté",
                        description=f"Un message potentiellement malveillant de {message.author.mention} a été supprimé.",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="Canal", value=message.channel.mention)
                    embed.add_field(name="Horodatage", value=message.created_at.strftime('%d/%m/%Y %H:%M:%S'))
                    
                    await log_channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Gestion des réactions pour la vérification."""
        # Ignorer les réactions du bot
        if payload.user_id == self.bot.user.id:
            return
        
        guild_id = str(payload.guild_id) if payload.guild_id else None
        
        # Vérifier si c'est une réaction dans un canal de vérification
        if guild_id and guild_id in self.verification_channels and str(payload.channel_id) == self.verification_channels[guild_id]:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return
                
            # Vérifier si c'est la bonne réaction
            if str(payload.emoji) == "✅":
                member = guild.get_member(payload.user_id)
                if not member:
                    return
                
                # Vérifier si le membre a le rôle "Non Vérifié"
                unverified_role = discord.utils.get(guild.roles, name="Non Vérifié")
                verified_role = discord.utils.get(guild.roles, name="Vérifié")
                
                if unverified_role and unverified_role in member.roles:
                    # Retirer le rôle "Non Vérifié"
                    try:
                        await member.remove_roles(unverified_role)
                    except Exception as e:
                        self.logger.error(f"Erreur lors du retrait du rôle Non Vérifié: {e}")
                    
                    # Ajouter le rôle "Vérifié"
                    if verified_role:
                        try:
                            await member.add_roles(verified_role)
                        except Exception as e:
                            self.logger.error(f"Erreur lors de l'attribution du rôle Vérifié: {e}")
                    
                    # Envoyer un message de bienvenue (système ou DM)
                    try:
                        await member.send(f"✅ Vérification réussie! Bienvenue sur **{guild.name}**.")
                    except:
                        pass
                    
                    # Log la vérification
                    self.logger.info(f"Membre {member.name}#{member.discriminator} vérifié sur {guild.name}")
    
    async def _check_join_rate(self, guild):
        """Vérifie le taux d'arrivées et active le verrouillage si nécessaire."""
        guild_id = str(guild.id)
        
        # Obtenir les arrivées de la dernière minute
        cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=1)
        recent_joins = [entry for entry in self.join_history[guild_id] if entry[1] > cutoff_time]
        
        # Récupérer les paramètres de protection
        config = SHIELD_LEVELS[self.shield_level]
        
        # Vérifier si le taux dépasse la limite
        if len(recent_joins) > config['join_rate_limit']:
            # Activer le verrouillage si pas déjà actif
            if not self._is_lockdown_active(guild_id):
                await self._enable_lockdown(guild, duration=30)  # 30 minutes par défaut
    
    async def _enable_lockdown(self, guild, duration=30):
        """Active le mode verrouillage sur un serveur."""
        guild_id = str(guild.id)
        
        # Définir le statut de verrouillage
        until_time = datetime.datetime.now() + datetime.timedelta(minutes=duration)
        self.lockdown_status[guild_id] = {
            'active': True,
            'until': until_time.timestamp(),
            'reason': 'Taux d\'arrivées anormal détecté'
        }
        
        # Sauvegarder les données
        self._save_data()
        
        # Log l'activation
        self.logger.warning(f"Mode verrouillage activé sur {guild.name} pour {duration} minutes")
        
        # Trouver le rôle everyone
        everyone_role = guild.default_role
        
        # Verrouiller les invitations
        try:
            await guild.edit(invites_disabled=True)
        except:
            pass
        
        # Annoncer dans le canal système
        system_channel = guild.system_channel
        if system_channel:
            embed = discord.Embed(
                title="🔒 Mode Verrouillage Activé",
                description=f"Suite à un flux anormal de nouveaux membres, le serveur est temporairement verrouillé.",
                color=discord.Color.red()
            )
            embed.add_field(name="Durée", value=f"{duration} minutes")
            embed.add_field(name="Fin prévue", value=until_time.strftime('%d/%m/%Y %H:%M:%S'))
            embed.set_footer(text="Les nouveaux membres seront automatiquement expulsés pendant cette période.")
            
            await system_channel.send(embed=embed)
        
        # Expulser les membres récemment arrivés (moins de 10 minutes)
        cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=10)
        recent_members = [member for member in guild.members if member.joined_at and member.joined_at.replace(tzinfo=None) > cutoff_time]
        
        for member in recent_members:
            try:
                await member.send(f"⚠️ Le serveur **{guild.name}** vient d'activer son mode verrouillage suite à une activité suspecte. Vous avez été expulsé par mesure de sécurité. Vous pourrez rejoindre à nouveau ultérieurement.")
            except:
                pass
            
            try:
                await member.kick(reason="Verrouillage de sécurité activé")
            except Exception as e:
                self.logger.error(f"Erreur lors de l'expulsion pendant le verrouillage: {e}")
    
    async def _disable_lockdown(self, guild_id):
        """Désactive le mode verrouillage sur un serveur."""
        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            # Supprimer l'entrée si le serveur n'existe plus
            if guild_id in self.lockdown_status:
                del self.lockdown_status[guild_id]
                self._save_data()
            return
        
        # Mettre à jour le statut
        self.lockdown_status[guild_id] = {'active': False}
        
        # Sauvegarder les données
        self._save_data()
        
        # Log la désactivation
        self.logger.info(f"Mode verrouillage désactivé sur {guild.name}")
        
        # Réactiver les invitations
        try:
            await guild.edit(invites_disabled=False)
        except:
            pass
        
        # Annoncer dans le canal système
        system_channel = guild.system_channel
        if system_channel:
            embed = discord.Embed(
                title="🔓 Mode Verrouillage Désactivé",
                description="Le serveur est de nouveau ouvert aux nouveaux membres.",
                color=discord.Color.green()
            )
            
            await system_channel.send(embed=embed)
    
    def _is_lockdown_active(self, guild_id):
        """Vérifie si un serveur est en mode verrouillage."""
        return guild_id in self.lockdown_status and self.lockdown_status[guild_id].get('active', False)
    
    def _is_trusted(self, member):
        """Vérifie si un membre est dans la liste de confiance."""
        return str(member.id) in self.trusted_members
    
    async def _is_suspicious(self, member):
        """Vérifie si un compte utilisateur est suspect."""
        # Vérifier l'âge du compte
        account_age = (datetime.datetime.now() - member.created_at).days
        if account_age < 1:  # Compte créé il y a moins d'un jour
            return True
        
        # Vérifier le nom d'utilisateur et le discriminateur
        username = f"{member.name}#{member.discriminator}" if hasattr(member, 'discriminator') else member.name
        
        # Vérifier les motifs suspects dans le nom
        for pattern in self.suspicious_patterns:
            if pattern.search(username) or pattern.search(member.display_name):
                return True
        
        # Vérifier le format du nom (suite de caractères aléatoires)
        if re.match(r"^[a-zA-Z0-9]{8,}$", member.name) and account_age < 7:
            return True
        
        return False
    
    async def _contains_malicious_content(self, message):
        """Vérifie si un message contient du contenu malveillant."""
        content = message.content.lower()
        
        # Vérifier les liens d'invitation Discord (hors membres de confiance)
        if "discord.gg/" in content and not message.author.guild_permissions.create_instant_invite:
            return True
        
        # Vérifier les motifs suspects dans le contenu
        for pattern in self.suspicious_patterns:
            if pattern.search(content):
                return True
        
        # Vérifier les URLs potentiellement dangereuses
        urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', content)
        for url in urls:
            # Liste de domaines suspects (à compléter au besoin)
            suspicious_domains = ["discordap.com", "discordnitro.fun", "discord-app.net", "steamcomunnity",
                               "dlscrod", "discocl", "discordgift", "steancommunity"]
            
            for domain in suspicious_domains:
                if domain in url:
                    return True
        
        # Vérifier les @everyone ou @here inappropriés
        if ("@everyone" in content or "@here" in content) and not message.author.guild_permissions.mention_everyone:
            return True
        
        return False
    
    @commands.group(name="shield", aliases=["bouclier"])
    @commands.has_permissions(administrator=True)
    async def shield_cmd(self, ctx):
        """Gestion du bouclier de protection du serveur."""
        if ctx.invoked_subcommand is None:
            await self._show_shield_status(ctx)
    
    @shield_cmd.command(name="level", aliases=["niveau"])
    async def shield_level_cmd(self, ctx, level: str):
        """Définit le niveau de protection du bouclier (low, medium, high, lockdown)."""
        if level.lower() not in SHIELD_LEVELS:
            await ctx.send(f"❌ Niveau de protection invalide. Choisissez parmi: {', '.join(SHIELD_LEVELS.keys())}")
            return
        
        self.shield_level = level.lower()
        
        # Sauvegarder la configuration
        self._save_data()
        
        # Créer un embed pour montrer les paramètres du niveau choisi
        config = SHIELD_LEVELS[self.shield_level]
        
        embed = discord.Embed(
            title=f"🛡️ Niveau de Protection: {self.shield_level.upper()}",
            description="Les paramètres du bouclier ont été mis à jour.",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Limite d'arrivées", value=f"{config['join_rate_limit']} membres/minute", inline=True)
        embed.add_field(name="Vérification", value=f"{'Requise' if config['verification_required'] else 'Non requise'}", inline=True)
        embed.add_field(name="Restriction d'invitations", value=f"{'Activée' if config['invite_restriction'] else 'Désactivée'}", inline=True)
        embed.add_field(name="Restriction des nouveaux comptes", value=f"{'Activée' if config['new_account_restriction'] else 'Désactivée'}", inline=True)
        embed.add_field(name="Ban auto. des comptes suspects", value=f"{'Activé' if config['auto_ban_suspicious'] else 'Désactivé'}", inline=True)
        
        await ctx.send(embed=embed)
        
        # Log le changement
        self.logger.info(f"Niveau de protection modifié à {self.shield_level} par {ctx.author.name}#{ctx.author.discriminator}")
        
        # Si lockdown, activer immédiatement
        if level.lower() == "lockdown":
            await self._enable_lockdown(ctx.guild, duration=60)
    
    @shield_cmd.command(name="status", aliases=["statut", "état", "etat"])
    async def shield_status_cmd(self, ctx):
        """Affiche le statut actuel et les paramètres du bouclier."""
        await self._show_shield_status(ctx)
    
    @shield_cmd.command(name="verify", aliases=["vérifier", "verification", "vérification"])
    async def shield_verify_cmd(self, ctx, channel: typing.Optional[discord.TextChannel] = None):
        """Définit le canal de vérification pour les nouveaux membres."""
        channel = channel or ctx.channel
        
        guild_id = str(ctx.guild.id)
        self.verification_channels[guild_id] = str(channel.id)
        
        # Sauvegarder la configuration
        self._save_data()
        
        await ctx.send(f"✅ Canal de vérification défini: {channel.mention}")
        
        # Vérifier que les rôles nécessaires existent
        unverified_role = discord.utils.get(ctx.guild.roles, name="Non Vérifié")
        verified_role = discord.utils.get(ctx.guild.roles, name="Vérifié")
        
        missing_roles = []
        if not unverified_role:
            missing_roles.append("Non Vérifié")
        if not verified_role:
            missing_roles.append("Vérifié")
        
        if missing_roles:
            await ctx.send(f"⚠️ Attention: Les rôles suivants n'existent pas: {', '.join(missing_roles)}\nVeuillez les créer pour que le système de vérification fonctionne correctement.")
    
    @shield_cmd.command(name="trust", aliases=["confiance"])
    async def shield_trust_cmd(self, ctx, member: discord.Member):
        """Ajoute un membre à la liste de confiance."""
        self.trusted_members.add(str(member.id))
        
        # Sauvegarder la configuration
        self._save_data()
        
        await ctx.send(f"✅ {member.mention} a été ajouté à la liste de confiance.")
        
        # Log l'action
        self.logger.info(f"{member.name}#{member.discriminator} ajouté à la liste de confiance par {ctx.author.name}#{ctx.author.discriminator}")
    
    @shield_cmd.command(name="untrust", aliases=["méfiance", "mefiance"])
    async def shield_untrust_cmd(self, ctx, member: discord.Member):
        """Retire un membre de la liste de confiance."""
        if str(member.id) in self.trusted_members:
            self.trusted_members.remove(str(member.id))
            
            # Sauvegarder la configuration
            self._save_data()
            
            await ctx.send(f"✅ {member.mention} a été retiré de la liste de confiance.")
            
            # Log l'action
            self.logger.info(f"{member.name}#{member.discriminator} retiré de la liste de confiance par {ctx.author.name}#{ctx.author.discriminator}")
        else:
            await ctx.send(f"❌ {member.mention} n'est pas dans la liste de confiance.")
    
    @shield_cmd.command(name="lockdown")
    async def shield_lockdown_cmd(self, ctx, duration: typing.Optional[int] = 30):
        """Active le mode verrouillage sur le serveur."""
        if duration < 5 or duration > 1440:
            await ctx.send("❌ La durée doit être entre 5 et 1440 minutes (24 heures).")
            return
        
        # Activer le verrouillage
        await self._enable_lockdown(ctx.guild, duration=duration)
        
        await ctx.send(f"🔒 Mode verrouillage activé pour {duration} minutes.")
    
    @shield_cmd.command(name="unlock", aliases=["déverrouiller", "deverrouiller"])
    async def shield_unlock_cmd(self, ctx):
        """Désactive le mode verrouillage sur le serveur."""
        guild_id = str(ctx.guild.id)
        
        if not self._is_lockdown_active(guild_id):
            await ctx.send("❌ Le serveur n'est pas en mode verrouillage.")
            return
        
        # Désactiver le verrouillage
        await self._disable_lockdown(guild_id)
        
        await ctx.send("🔓 Mode verrouillage désactivé.")
    
    async def _show_shield_status(self, ctx):
        """Affiche les informations sur la configuration du bouclier actuel."""
        config = SHIELD_LEVELS[self.shield_level]
        guild_id = str(ctx.guild.id)
        
        embed = discord.Embed(
            title="🛡️ Statut du Bouclier de Protection",
            description=f"**Niveau actuel**: {self.shield_level.upper()}",
            color=discord.Color.blue()
        )
        
        # Statut du verrouillage
        lockdown_status = "Actif" if self._is_lockdown_active(guild_id) else "Inactif"
        lockdown_color = "🔴" if self._is_lockdown_active(guild_id) else "🟢"
        
        # Canal de vérification
        verification_channel = None
        if guild_id in self.verification_channels:
            channel_id = int(self.verification_channels[guild_id])
            verification_channel = ctx.guild.get_channel(channel_id)
        
        # Statistiques
        embed.add_field(name="Statut du verrouillage", value=f"{lockdown_color} {lockdown_status}", inline=True)
        embed.add_field(name="Canal de vérification", value=verification_channel.mention if verification_channel else "Non configuré", inline=True)
        embed.add_field(name="Membres de confiance", value=f"{len(self.trusted_members)}", inline=True)
        
        # Paramètres actuels
        embed.add_field(name="Paramètres de Protection", value="\u200b", inline=False)
        embed.add_field(name="Limite d'arrivées", value=f"{config['join_rate_limit']} membres/minute", inline=True)
        embed.add_field(name="Vérification", value=f"{'Requise' if config['verification_required'] else 'Non requise'}", inline=True)
        embed.add_field(name="Restriction d'invitations", value=f"{'Activée' if config['invite_restriction'] else 'Désactivée'}", inline=True)
        embed.add_field(name="Restriction des nouveaux comptes", value=f"{'Activée' if config['new_account_restriction'] else 'Désactivée'}", inline=True)
        embed.add_field(name="Ban auto. des comptes suspects", value=f"{'Activé' if config['auto_ban_suspicious'] else 'Désactivé'}", inline=True)
        
        # Informations sur les actions récentes
        if guild_id in self.action_logs and self.action_logs[guild_id]:
            recent_actions = self.action_logs[guild_id][-5:]  # 5 dernières actions
            
            action_text = "\n".join([f"• {action['time'].strftime('%H:%M:%S')} - {action['action']}: {action['target']}" 
                                   for action in recent_actions])
            
            embed.add_field(name="Actions récentes", value=action_text or "Aucune action récente", inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Ajoute le cog de bouclier au bot."""
    await bot.add_cog(Shield(bot))