"""
Module de messagerie directe pour LeSéminaire[BOT].
Gère l'envoi de messages privés aux membres pour les annonces et le système de bienvenue.
"""

import discord
from discord.ext import commands
import asyncio
import logging
import typing
import datetime
from datetime import timedelta

# Configuration du logger
logger = logging.getLogger('le_seminaire.messenger')

class Messenger(commands.Cog):
    """Système de messagerie directe du bot LeSéminaire."""

    def __init__(self, bot):
        self.bot = bot
        # File d'attente des annonces à envoyer
        self.pending_announcements = []
        self.announcement_task = self.bot.loop.create_task(self.process_announcement_queue())
        
        # Accès à la base de données via database.py
        from database import DatabaseManager
        self.db = DatabaseManager()

    def _get_user_preferences(self, user_id):
        """Récupère les préférences de messagerie d'un utilisateur depuis la base de données."""
        from models import MessagePreference
        
        try:
            session = self.db.get_session()
            pref = session.query(MessagePreference).filter_by(user_id=str(user_id)).first()
            
            if not pref:
                # Créer une entrée par défaut si elle n'existe pas
                pref = MessagePreference(user_id=str(user_id), opt_out=False)
                session.add(pref)
                session.commit()
            
            return pref
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des préférences de l'utilisateur {user_id}: {str(e)}")
            return None
        finally:
            session.close()

    def _is_user_opted_out(self, user_id):
        """Vérifie si un utilisateur a désactivé les messages du bot."""
        pref = self._get_user_preferences(user_id)
        return pref and pref.opt_out

    def _set_user_opt_out(self, user_id, opt_out=True):
        """Définit l'état d'opt-out d'un utilisateur."""
        from models import MessagePreference
        
        try:
            session = self.db.get_session()
            pref = session.query(MessagePreference).filter_by(user_id=str(user_id)).first()
            
            if not pref:
                pref = MessagePreference(user_id=str(user_id), opt_out=opt_out)
                session.add(pref)
            else:
                pref.opt_out = opt_out
            
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la définition des préférences de l'utilisateur {user_id}: {str(e)}")
            return False
        finally:
            session.close()

    def _update_last_dm_time(self, user_id):
        """Met à jour l'horodatage du dernier message envoyé à un utilisateur."""
        from models import MessagePreference
        import datetime
        
        try:
            session = self.db.get_session()
            pref = session.query(MessagePreference).filter_by(user_id=str(user_id)).first()
            
            if not pref:
                pref = MessagePreference(user_id=str(user_id), last_dm=datetime.datetime.utcnow())
                session.add(pref)
            else:
                pref.last_dm = datetime.datetime.utcnow()
            
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'horodatage pour l'utilisateur {user_id}: {str(e)}")
            return False
        finally:
            session.close()

    def _check_dm_cooldown(self, user_id):
        """Vérifie si un utilisateur est en cooldown pour les DMs."""
        from models import MessagePreference
        import datetime
        
        try:
            session = self.db.get_session()
            pref = session.query(MessagePreference).filter_by(user_id=str(user_id)).first()
            
            if not pref or not pref.last_dm:
                return False  # Pas de cooldown si pas d'entrée ou pas de dernier DM
            
            # Vérifier si 24 heures se sont écoulées depuis le dernier DM
            now = datetime.datetime.utcnow()
            cooldown_expired = now - pref.last_dm > datetime.timedelta(hours=24)
            
            return not cooldown_expired  # True si toujours en cooldown
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du cooldown pour l'utilisateur {user_id}: {str(e)}")
            return False  # En cas d'erreur, on permet l'envoi
        finally:
            session.close()

    def cog_unload(self):
        """Nettoyage lors du déchargement du cog."""
        if self.announcement_task:
            self.announcement_task.cancel()

    async def process_announcement_queue(self):
        """Traite la file d'attente des annonces pour éviter le rate limiting."""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                if self.pending_announcements:
                    # Récupérer la prochaine annonce de la file
                    announcement = self.pending_announcements.pop(0)
                    guild_id = announcement['guild_id']
                    message = announcement['message']
                    filter_roles = announcement.get('filter_roles', [])
                    
                    guild = self.bot.get_guild(int(guild_id))
                    if not guild:
                        logger.error(f"Impossible de trouver le serveur ID: {guild_id}")
                        continue
                    
                    # Filtrer les membres en fonction des rôles si nécessaire
                    members = []
                    if filter_roles:
                        role_ids = [int(r) for r in filter_roles]
                        for member in guild.members:
                            member_role_ids = [role.id for role in member.roles]
                            if any(r in member_role_ids for r in role_ids):
                                members.append(member)
                    else:
                        members = guild.members
                    
                    # Envoyer l'annonce à chaque membre
                    success_count = 0
                    failed_count = 0
                    opted_out_count = 0
                    
                    for member in members:
                        # Ignorer les bots et les utilisateurs ayant désactivé les DMs
                        if member.bot:
                            continue
                            
                        if self._is_user_opted_out(member.id):
                            opted_out_count += 1
                            continue
                        
                        # Vérifier les cooldowns
                        if self._check_dm_cooldown(member.id):
                            continue
                        
                        try:
                            await member.send(message)
                            self._update_last_dm_time(member.id)
                            success_count += 1
                            
                            # Pause pour éviter le rate limiting
                            await asyncio.sleep(1.5)
                        except discord.Forbidden:
                            failed_count += 1
                            logger.warning(f"Impossible d'envoyer un DM à {member.name}#{member.discriminator} (ID: {member.id})")
                        except Exception as e:
                            failed_count += 1
                            logger.error(f"Erreur lors de l'envoi d'un DM à {member.name}#{member.discriminator}: {str(e)}")
                    
                    # Journaliser les résultats
                    logger.info(f"Annonce envoyée: {success_count} succès, {failed_count} échecs, {opted_out_count} désactivés")
                
                # Attendre avant de traiter le prochain lot
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Erreur dans la file d'annonces: {str(e)}")
                await asyncio.sleep(30)  # Pause plus longue en cas d'erreur

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Envoie un message de bienvenue aux nouveaux membres."""
        if member.bot or self._is_user_opted_out(member.id):
            return
        
        # Créer un embed de bienvenue
        embed = discord.Embed(
            title=f"Bienvenue sur Le Séminaire, {member.name}!",
            description="Merci de rejoindre notre communauté artistique. Nous sommes ravis de t'accueillir!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="👋 Présente-toi",
            value="N'hésite pas à te présenter dans le canal #présentations et à interagir avec la communauté!",
            inline=False
        )
        
        embed.add_field(
            name="🔗 Rejoins-nous sur nos autres plateformes",
            value="[Linktree du Séminaire](https://linktr.ee/LeSeminaire)",
            inline=False
        )
        
        embed.add_field(
            name="🎭 Obtiens tes rôles",
            value="Visite le canal #roles pour choisir tes rôles et spécialités artistiques!",
            inline=False
        )
        
        embed.add_field(
            name="📜 Règles",
            value="N'oublie pas de lire les règles du serveur et de réagir pour obtenir l'accès complet.",
            inline=False
        )
        
        embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else discord.Embed.Empty)
        embed.set_footer(text="Pour désactiver les messages du bot, tape !optout")
        
        try:
            await member.send(embed=embed)
            logger.info(f"Message de bienvenue envoyé à {member.name}#{member.discriminator}")
        except discord.Forbidden:
            logger.warning(f"Impossible d'envoyer un message de bienvenue à {member.name}#{member.discriminator}")
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message de bienvenue: {str(e)}")

    @commands.group(name="dm", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def dm_group(self, ctx):
        """Commandes pour la gestion des messages directs."""
        await ctx.send_help(ctx.command)

    @dm_group.command(name="send")
    @commands.has_permissions(administrator=True)
    async def dm_send_cmd(self, ctx, *, message: str):
        """
        Envoie un message privé à tous les membres du serveur.
        
        Exemple:
        !dm send Salut à tous! Nouvel événement demain à 20h!
        """
        # Demander confirmation
        confirmation_message = await ctx.send(
            f"⚠️ **Confirmation requise** ⚠️\n"
            f"Tu es sur le point d'envoyer un DM à **{len(ctx.guild.members) - 1}** membres.\n"
            f"```{message}```\n"
            f"Es-tu sûr de vouloir continuer? (oui/non)"
        )
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['oui', 'non', 'yes', 'no']
        
        try:
            response = await self.bot.wait_for('message', check=check, timeout=60)
            
            if response.content.lower() in ['non', 'no']:
                await confirmation_message.delete()
                return await ctx.send("Envoi annulé.")
            
            announcement = {
                'guild_id': str(ctx.guild.id),
                'message': message,
                'filter_roles': []
            }
            
            self.pending_announcements.append(announcement)
            await ctx.send(f"✅ Message ajouté à la file d'attente! Il sera envoyé progressivement aux membres.")
            
        except asyncio.TimeoutError:
            await confirmation_message.delete()
            await ctx.send("Délai d'attente dépassé. Veuillez réessayer.")

    @dm_group.command(name="announce")
    @commands.has_permissions(administrator=True)
    async def dm_announce_cmd(self, ctx, *, announcement: str):
        """
        Envoie une annonce à tous les membres du serveur.
        Le message sera formaté automatiquement avec un en-tête et un pied de page.
        
        Exemple:
        !dm announce Nouvel événement ce weekend! Venez nombreux!
        """
        formatted_message = (
            f"📢 **Annonce de {ctx.guild.name}** 📢\n\n"
            f"{announcement}\n\n"
            f"🔗 Rejoignez-nous: https://linktr.ee/LeSeminaire\n"
            f"_Pour désactiver ces messages, utilisez la commande `!optout`_"
        )
        
        # Appeler la commande d'envoi avec le message formaté
        await self.dm_send_cmd(ctx, message=formatted_message)

    @dm_group.command(name="event")
    @commands.has_permissions(administrator=True)
    async def dm_event_cmd(self, ctx, date: str, heure: str, *, description: str):
        """
        Envoie une invitation d'événement à tous les membres.
        
        Exemple:
        !dm event 21/07/2025 20:00 Session d'enregistrement au studio
        """
        event_message = (
            f"🗓️ **Événement à venir** 🗓️\n\n"
            f"📅 Date: **{date}**\n"
            f"⏰ Heure: **{heure}**\n\n"
            f"📝 **Description:**\n{description}\n\n"
            f"🔗 Plus d'infos: https://linktr.ee/LeSeminaire\n"
            f"_Pour désactiver ces messages, utilisez la commande `!optout`_"
        )
        
        # Appeler la commande d'envoi avec le message formaté
        await self.dm_send_cmd(ctx, message=event_message)

    @dm_group.command(name="role")
    @commands.has_permissions(administrator=True)
    async def dm_role_cmd(self, ctx, role: discord.Role, *, message: str):
        """
        Envoie un message privé à tous les membres ayant un rôle spécifique.
        
        Exemple:
        !dm role @Artiste Message spécial pour les artistes!
        """
        members_with_role = [member for member in ctx.guild.members if role in member.roles]
        
        if not members_with_role:
            return await ctx.send(f"Aucun membre n'a le rôle {role.name}.")
        
        # Demander confirmation
        confirmation_message = await ctx.send(
            f"⚠️ **Confirmation requise** ⚠️\n"
            f"Tu es sur le point d'envoyer un DM à **{len(members_with_role)}** membres avec le rôle {role.name}.\n"
            f"```{message}```\n"
            f"Es-tu sûr de vouloir continuer? (oui/non)"
        )
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['oui', 'non', 'yes', 'no']
        
        try:
            response = await self.bot.wait_for('message', check=check, timeout=60)
            
            if response.content.lower() in ['non', 'no']:
                await confirmation_message.delete()
                return await ctx.send("Envoi annulé.")
            
            announcement = {
                'guild_id': str(ctx.guild.id),
                'message': message,
                'filter_roles': [str(role.id)]
            }
            
            self.pending_announcements.append(announcement)
            await ctx.send(f"✅ Message ajouté à la file d'attente! Il sera envoyé progressivement aux membres avec le rôle {role.name}.")
            
        except asyncio.TimeoutError:
            await confirmation_message.delete()
            await ctx.send("Délai d'attente dépassé. Veuillez réessayer.")

    @commands.command(name="optout")
    async def optout_cmd(self, ctx):
        """
        Désactive la réception des messages du bot.
        Les messages importants liés à la modération pourront toujours être envoyés.
        """
        if ctx.guild is None:  # Commande utilisée en DM
            user_id = ctx.author.id
            
            if self._is_user_opted_out(user_id):
                await ctx.send("Vous êtes déjà désabonné des messages du bot.")
            else:
                success = self._set_user_opt_out(user_id, True)
                if success:
                    await ctx.send("✅ Vous êtes maintenant désabonné des messages du bot. Pour vous réabonner, utilisez `!optin`.")
                else:
                    await ctx.send("❌ Une erreur s'est produite lors du désabonnement. Veuillez réessayer.")
        else:  # Commande utilisée sur le serveur
            await ctx.send("Pour votre confidentialité, veuillez utiliser cette commande en message privé.")
            try:
                await ctx.author.send("Pour désactiver les messages du bot, utilisez la commande `!optout` ici en message privé.")
            except discord.Forbidden:
                await ctx.send("Je n'ai pas pu vous envoyer de message privé. Veuillez vérifier vos paramètres de confidentialité.")

    @commands.command(name="optin")
    async def optin_cmd(self, ctx):
        """
        Réactive la réception des messages du bot.
        """
        if ctx.guild is None:  # Commande utilisée en DM
            user_id = ctx.author.id
            
            if not self._is_user_opted_out(user_id):
                await ctx.send("Vous êtes déjà abonné aux messages du bot.")
            else:
                success = self._set_user_opt_out(user_id, False)
                if success:
                    await ctx.send("✅ Vous êtes maintenant réabonné aux messages du bot. Pour vous désabonner, utilisez `!optout`.")
                else:
                    await ctx.send("❌ Une erreur s'est produite lors du réabonnement. Veuillez réessayer.")
        else:  # Commande utilisée sur le serveur
            await ctx.send("Pour votre confidentialité, veuillez utiliser cette commande en message privé.")
            try:
                await ctx.author.send("Pour réactiver les messages du bot, utilisez la commande `!optin` ici en message privé.")
            except discord.Forbidden:
                await ctx.send("Je n'ai pas pu vous envoyer de message privé. Veuillez vérifier vos paramètres de confidentialité.")

    @commands.command(name="residency", aliases=["residence"])
    async def residency_cmd(self, ctx):
        """
        Envoie en message privé les informations sur la prochaine résidence.
        """
        # Informations sur la résidence actuelle/prochaine
        residency_info = "Concarneau : 21 au 26 juillet 2025"
        
        embed = discord.Embed(
            title="🏝️ Prochaine Résidence du Séminaire",
            description=f"**{residency_info}**",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="🎵 Programme",
            value="• Sessions d'enregistrement\n• Ateliers d'écriture\n• Collaborations\n• Concerts",
            inline=False
        )
        
        embed.add_field(
            name="📍 Lieu",
            value="Studio Le Séminaire\nConcarneau, Bretagne",
            inline=True
        )
        
        embed.add_field(
            name="👥 Participants",
            value="Artistes sélectionnés\n(places limitées)",
            inline=True
        )
        
        embed.add_field(
            name="🔗 Plus d'informations",
            value="[Linktree du Séminaire](https://linktr.ee/LeSeminaire)",
            inline=False
        )
        
        embed.set_footer(text="Pour tout renseignement supplémentaire, contactez un administrateur")
        
        try:
            await ctx.author.send(embed=embed)
            if ctx.guild:  # Si la commande est utilisée sur un serveur
                await ctx.send("📬 Informations sur la résidence envoyées en message privé!")
        except discord.Forbidden:
            await ctx.send("❌ Je n'ai pas pu vous envoyer de message privé. Veuillez vérifier vos paramètres de confidentialité.")
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi des informations de résidence: {str(e)}")
            await ctx.send("Une erreur s'est produite lors de l'envoi du message.")

    @dm_group.command(name="welcome")
    @commands.has_permissions(administrator=True)
    async def dm_welcome_cmd(self, ctx, member: discord.Member):
        """
        Envoie un message de bienvenue personnalisé à un membre spécifique.
        
        Exemple:
        !dm welcome @Utilisateur
        """
        if member.bot:
            return await ctx.send("❌ Impossible d'envoyer un message à un bot.")
        
        if self._is_user_opted_out(member.id):
            return await ctx.send(f"⚠️ {member.mention} a désactivé la réception des messages du bot.")
        
        # Créer un embed de bienvenue personnalisé
        embed = discord.Embed(
            title=f"Bienvenue sur Le Séminaire, {member.name}!",
            description=f"Message personnalisé de {ctx.author.mention} !\nMerci de rejoindre notre communauté artistique. Nous sommes ravis de t'accueillir!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="👋 Présente-toi",
            value="N'hésite pas à te présenter dans le canal #présentations et à interagir avec la communauté!",
            inline=False
        )
        
        embed.add_field(
            name="🔗 Rejoins-nous sur nos autres plateformes",
            value="[Linktree du Séminaire](https://linktr.ee/LeSeminaire)",
            inline=False
        )
        
        embed.add_field(
            name="📩 Message de l'équipe",
            value="N'hésite pas à contacter un membre de l'équipe si tu as des questions!",
            inline=False
        )
        
        embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else discord.Embed.Empty)
        embed.set_footer(text="Pour désactiver les messages du bot, tape !optout")
        
        try:
            await member.send(embed=embed)
            await ctx.send(f"✅ Message de bienvenue personnalisé envoyé à {member.mention}!")
            logger.info(f"Message de bienvenue personnalisé envoyé à {member.name}#{member.discriminator} par {ctx.author.name}")
        except discord.Forbidden:
            await ctx.send(f"❌ Impossible d'envoyer un message privé à {member.mention}. Leurs paramètres de confidentialité ne le permettent pas.")
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message de bienvenue personnalisé: {str(e)}")
            await ctx.send(f"❌ Une erreur s'est produite lors de l'envoi du message à {member.mention}.")

async def setup(bot):
    """Ajoute le cog de messagerie au bot."""
    await bot.add_cog(Messenger(bot))