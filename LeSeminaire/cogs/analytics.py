"""
Module d'analytique pour LeSéminaire[BOT].
Collecte et traite les données d'engagement et d'activité du serveur.
"""

import discord
from discord.ext import commands, tasks
import asyncio
import datetime
import logging
import json
import typing
import os
from collections import defaultdict, Counter

# Configuration du logger
logger = logging.getLogger('le_seminaire.analytics')

class ServerAnalytics(commands.Cog):
    """Système d'analytique et de visualisation pour LeSéminaire[BOT]."""

    def __init__(self, bot):
        self.bot = bot
        self.activity_data = defaultdict(lambda: defaultdict(int))
        self.message_activity = defaultdict(int)
        self.voice_activity = defaultdict(int)
        self.reaction_activity = defaultdict(int)
        self.emoji_usage = Counter()
        self.user_join_data = []
        self.user_leave_data = []
        self.active_hour_data = defaultdict(int)
        self.active_day_data = defaultdict(int)
        self.channel_activity = defaultdict(int)
        
        # Accès à la base de données via database.py
        from database import DatabaseManager
        self.db = DatabaseManager()
        
        # Démarrer les tâches périodiques
        self.save_analytics_task.start()
        self.weekly_report_task.start()
        self.daily_analytics_cleanup.start()
        
        # Charger les données existantes
        self._load_analytics_data()
    
    def _load_analytics_data(self):
        """Charge les données d'analytique depuis la base de données."""
        try:
            from models import ServerStat
            session = self.db.get_session()
            
            # Récupérer les statistiques des 30 derniers jours
            thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
            recent_stats = session.query(ServerStat).filter(
                ServerStat.timestamp >= thirty_days_ago
            ).order_by(ServerStat.timestamp.desc()).all()
            
            if recent_stats:
                # Traiter les statistiques pour initialiser les données d'analytics
                for stat in recent_stats:
                    try:
                        data = json.loads(stat.data) if stat.data else {}
                        
                        # Date de la statistique (pour regrouper par jour)
                        stat_date = stat.timestamp.strftime('%Y-%m-%d')
                        
                        # Activité du jour
                        if 'message_count' in data:
                            self.activity_data[stat_date]['messages'] += data['message_count']
                        
                        if 'voice_minutes' in data:
                            self.activity_data[stat_date]['voice'] += data['voice_minutes']
                        
                        if 'reaction_count' in data:
                            self.activity_data[stat_date]['reactions'] += data['reaction_count']
                        
                        # Heures actives
                        hour = stat.timestamp.hour
                        self.active_hour_data[hour] += data.get('message_count', 0)
                        
                        # Jours actifs
                        weekday = stat.timestamp.weekday()
                        self.active_day_data[weekday] += data.get('message_count', 0)
                        
                    except Exception as e:
                        logger.error(f"Erreur lors du traitement des statistiques: {e}")
            
            logger.info(f"Données d'analytique chargées: {len(recent_stats)} entrées")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données d'analytique: {e}")
        finally:
            if 'session' in locals():
                session.close()
    
    def cog_unload(self):
        """Nettoyage lors du déchargement du cog."""
        self.save_analytics_task.cancel()
        self.weekly_report_task.cancel()
        self.daily_analytics_cleanup.cancel()
    
    @tasks.loop(hours=1)
    async def save_analytics_task(self):
        """Sauvegarde les données d'analytique dans la base de données."""
        try:
            from models import ServerStat
            
            # Créer un snapshot des données actuelles
            now = datetime.datetime.utcnow()
            data = {
                'message_count': sum(self.message_activity.values()),
                'voice_minutes': sum(self.voice_activity.values()),
                'reaction_count': sum(self.reaction_activity.values()),
                'active_channels': {str(k): v for k, v in self.channel_activity.items() if v > 0},
                'emoji_usage': {emoji: count for emoji, count in self.emoji_usage.most_common(10)},
                'active_users': len(self.message_activity)
            }
            
            # Réinitialiser les compteurs temporaires
            self.message_activity = defaultdict(int)
            self.voice_activity = defaultdict(int)
            self.reaction_activity = defaultdict(int)
            self.channel_activity = defaultdict(int)
            self.emoji_usage = Counter()
            
            # Sauvegarder dans la base de données
            session = self.db.get_session()
            stat = ServerStat(
                timestamp=now,
                guild_id=self.bot.guilds[0].id if self.bot.guilds else None,
                type='hourly',
                data=json.dumps(data)
            )
            session.add(stat)
            session.commit()
            logger.info(f"Données d'analytique sauvegardées: {data}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des données d'analytique: {e}")
        finally:
            if 'session' in locals():
                session.close()
    
    @save_analytics_task.before_loop
    async def before_save_analytics(self):
        """Attendre que le bot soit prêt avant de démarrer la tâche."""
        await self.bot.wait_until_ready()
        await asyncio.sleep(300)  # Attendre 5 minutes après le démarrage pour commencer
    
    @tasks.loop(hours=24)
    async def weekly_report_task(self):
        """Génère et envoie un rapport hebdomadaire aux administrateurs."""
        # Vérifier si c'est le jour de la semaine pour le rapport (par exemple, dimanche = 6)
        if datetime.datetime.utcnow().weekday() != 6:
            return
        
        try:
            # Trouver le premier administrateur/propriétaire pour envoyer le rapport
            for guild in self.bot.guilds:
                owner = guild.owner
                if owner:
                    await self._send_weekly_report(owner, guild)
                    break
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du rapport hebdomadaire: {e}")
    
    @weekly_report_task.before_loop
    async def before_weekly_report(self):
        """Attendre que le bot soit prêt avant de démarrer la tâche."""
        await self.bot.wait_until_ready()
    
    @tasks.loop(hours=24)
    async def daily_analytics_cleanup(self):
        """Nettoie les anciennes données d'analytique."""
        try:
            from models import ServerStat
            
            # Supprimer les données de plus de 90 jours
            ninety_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=90)
            
            session = self.db.get_session()
            old_records = session.query(ServerStat).filter(
                ServerStat.timestamp < ninety_days_ago
            ).delete()
            
            session.commit()
            logger.info(f"Nettoyage des données d'analytique: {old_records} enregistrements supprimés")
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des données d'analytique: {e}")
        finally:
            if 'session' in locals():
                session.close()
    
    @daily_analytics_cleanup.before_loop
    async def before_daily_cleanup(self):
        """Attendre que le bot soit prêt avant de démarrer la tâche."""
        await self.bot.wait_until_ready()
        
        # Calculer le temps jusqu'à 3h du matin pour faire le nettoyage
        now = datetime.datetime.utcnow()
        future = datetime.datetime(now.year, now.month, now.day, 3, 0)
        if now.hour >= 3:
            future += datetime.timedelta(days=1)
        
        seconds = (future - now).total_seconds()
        await asyncio.sleep(seconds)
    
    async def _send_weekly_report(self, user, guild):
        """Envoie un rapport hebdomadaire à l'utilisateur spécifié."""
        embed = discord.Embed(
            title=f"📊 Rapport hebdomadaire - {guild.name}",
            description="Résumé de l'activité du serveur pour la semaine passée",
            color=discord.Color.blue()
        )
        
        # Calculer les statistiques de la semaine
        one_week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        week_ago_str = one_week_ago.strftime('%Y-%m-%d')
        
        # Messages totaux de la semaine
        total_messages = sum(self.activity_data[date]['messages'] for date in self.activity_data 
                            if week_ago_str <= date <= today)
        
        # Minutes vocales totales de la semaine
        total_voice = sum(self.activity_data[date]['voice'] for date in self.activity_data 
                          if week_ago_str <= date <= today)
        
        # Réactions totales de la semaine
        total_reactions = sum(self.activity_data[date]['reactions'] for date in self.activity_data 
                             if week_ago_str <= date <= today)
        
        # Nouveaux membres
        new_members = len([data for data in self.user_join_data 
                          if data.get('timestamp') and data['timestamp'] >= one_week_ago])
        
        # Membres partis
        left_members = len([data for data in self.user_leave_data 
                           if data.get('timestamp') and data['timestamp'] >= one_week_ago])
        
        # Ajouter les champs au rapport
        embed.add_field(name="📝 Messages", value=f"{total_messages:,}", inline=True)
        embed.add_field(name="🎤 Minutes vocales", value=f"{total_voice:,}", inline=True)
        embed.add_field(name="👍 Réactions", value=f"{total_reactions:,}", inline=True)
        embed.add_field(name="📈 Nouveaux membres", value=f"{new_members:,}", inline=True)
        embed.add_field(name="📉 Départs", value=f"{left_members:,}", inline=True)
        
        # Jours les plus actifs
        day_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        most_active_day = max(self.active_day_data.items(), key=lambda x: x[1], default=(0, 0))
        if most_active_day[1] > 0:
            embed.add_field(
                name="📅 Jour le plus actif",
                value=day_names[most_active_day[0]],
                inline=True
            )
        
        # Heures les plus actives
        most_active_hour = max(self.active_hour_data.items(), key=lambda x: x[1], default=(0, 0))
        if most_active_hour[1] > 0:
            embed.add_field(
                name="⏰ Heure la plus active",
                value=f"{most_active_hour[0]:02d}:00 UTC",
                inline=True
            )
        
        embed.set_footer(text=f"Période: {week_ago_str} - {today}")
        
        try:
            await user.send(embed=embed)
            logger.info(f"Rapport hebdomadaire envoyé à {user.name}")
        except discord.Forbidden:
            logger.warning(f"Impossible d'envoyer le rapport hebdomadaire à {user.name}")
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du rapport hebdomadaire: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Collecte des données sur les messages."""
        if message.author.bot:
            return
        
        # Incrémenter l'activité par utilisateur
        self.message_activity[message.author.id] += 1
        
        # Incrémenter l'activité par canal
        self.channel_activity[message.channel.id] += 1
        
        # Enregistrer l'heure active
        hour = datetime.datetime.utcnow().hour
        self.active_hour_data[hour] += 1
        
        # Enregistrer le jour actif
        weekday = datetime.datetime.utcnow().weekday()
        self.active_day_data[weekday] += 1
        
        # Enregistrer l'activité quotidienne
        today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        self.activity_data[today]['messages'] += 1
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Collecte des données sur les réactions."""
        if user.bot:
            return
        
        # Incrémenter l'activité de réaction par utilisateur
        self.reaction_activity[user.id] += 1
        
        # Compteur d'emojis
        emoji_name = str(reaction.emoji)
        self.emoji_usage[emoji_name] += 1
        
        # Enregistrer l'activité quotidienne
        today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        self.activity_data[today]['reactions'] += 1
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Collecte des données sur l'activité vocale."""
        if member.bot:
            return
        
        # Si l'utilisateur rejoint un canal vocal
        if before.channel is None and after.channel is not None:
            # Stocker l'heure de début pour calculer la durée plus tard
            member._voice_join_time = datetime.datetime.utcnow()
        
        # Si l'utilisateur quitte un canal vocal
        elif before.channel is not None and (after.channel is None or after.channel != before.channel):
            join_time = getattr(member, '_voice_join_time', None)
            if join_time:
                # Calculer la durée en minutes
                now = datetime.datetime.utcnow()
                duration = (now - join_time).total_seconds() / 60
                
                # Incrémenter l'activité vocale par utilisateur
                self.voice_activity[member.id] += duration
                
                # Enregistrer l'activité quotidienne
                today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
                self.activity_data[today]['voice'] += duration
                
                # Nettoyer la donnée temporaire
                del member._voice_join_time
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Collecte des données sur les nouveaux membres."""
        self.user_join_data.append({
            'user_id': member.id,
            'timestamp': datetime.datetime.utcnow(),
            'guild_id': member.guild.id
        })
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Collecte des données sur les membres qui partent."""
        self.user_leave_data.append({
            'user_id': member.id,
            'timestamp': datetime.datetime.utcnow(),
            'guild_id': member.guild.id
        })
    
    @commands.group(name="analytics", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def analytics_group(self, ctx):
        """Commandes d'analytique et statistiques."""
        await ctx.send_help(ctx.command)
    
    @analytics_group.command(name="report")
    @commands.has_permissions(administrator=True)
    async def analytics_report_cmd(self, ctx):
        """Génère un rapport sur l'activité du serveur."""
        await self._send_weekly_report(ctx.author, ctx.guild)
        await ctx.send("✅ Rapport d'activité envoyé en message privé!")
    
    @analytics_group.command(name="status")
    @commands.has_permissions(administrator=True)
    async def analytics_status_cmd(self, ctx):
        """Affiche un aperçu rapide de l'état actuel du serveur."""
        guild = ctx.guild
        
        total_members = guild.member_count
        online_members = len([m for m in guild.members if m.status != discord.Status.offline])
        bot_count = len([m for m in guild.members if m.bot])
        human_members = total_members - bot_count
        
        # Canaux et catégories
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        # Activité récente
        today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        yesterday = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        today_messages = self.activity_data[today]['messages']
        yesterday_messages = self.activity_data[yesterday]['messages']
        
        # Membres en vocal
        members_in_voice = sum(1 for m in guild.members if m.voice)
        
        embed = discord.Embed(
            title=f"📊 État du serveur - {guild.name}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="👥 Membres total", value=f"{total_members:,}", inline=True)
        embed.add_field(name="🟢 Membres en ligne", value=f"{online_members:,}", inline=True)
        embed.add_field(name="🤖 Bots", value=f"{bot_count:,}", inline=True)
        
        embed.add_field(name="💬 Canaux textuels", value=f"{text_channels:,}", inline=True)
        embed.add_field(name="🔊 Canaux vocaux", value=f"{voice_channels:,}", inline=True)
        embed.add_field(name="📚 Catégories", value=f"{categories:,}", inline=True)
        
        embed.add_field(name="📝 Messages aujourd'hui", value=f"{today_messages:,}", inline=True)
        embed.add_field(name="📜 Messages hier", value=f"{yesterday_messages:,}", inline=True)
        embed.add_field(name="🎤 En vocal maintenant", value=f"{members_in_voice:,}", inline=True)
        
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        embed.set_footer(text=f"ID du serveur: {guild.id} • Créé le {guild.created_at.strftime('%d/%m/%Y')}")
        
        await ctx.send(embed=embed)
    
    @analytics_group.command(name="activity")
    @commands.has_permissions(administrator=True)
    async def analytics_activity_cmd(self, ctx, days: typing.Optional[int] = 7):
        """
        Affiche l'activité du serveur sur une période donnée.
        
        Exemple:
        !analytics activity 14
        """
        if days < 1 or days > 30:
            return await ctx.send("❌ Le nombre de jours doit être compris entre 1 et 30.")
        
        # Calculer les dates
        today = datetime.datetime.utcnow()
        start_date = today - datetime.timedelta(days=days)
        date_range = [(start_date + datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days + 1)]
        
        # Préparer les données d'activité
        message_data = [self.activity_data[date]['messages'] for date in date_range]
        voice_data = [round(self.activity_data[date]['voice']) for date in date_range]
        reaction_data = [self.activity_data[date]['reactions'] for date in date_range]
        
        embed = discord.Embed(
            title=f"📊 Activité sur {days} jours - {ctx.guild.name}",
            color=discord.Color.blue()
        )
        
        # Activité totale
        total_messages = sum(message_data)
        total_voice = sum(voice_data)
        total_reactions = sum(reaction_data)
        
        embed.add_field(name="📝 Messages totaux", value=f"{total_messages:,}", inline=True)
        embed.add_field(name="🎤 Minutes vocales", value=f"{total_voice:,}", inline=True)
        embed.add_field(name="👍 Réactions", value=f"{total_reactions:,}", inline=True)
        
        # Moyennes quotidiennes
        avg_messages = round(total_messages / days) if days > 0 else 0
        avg_voice = round(total_voice / days) if days > 0 else 0
        avg_reactions = round(total_reactions / days) if days > 0 else 0
        
        embed.add_field(name="📝 Messages/jour", value=f"{avg_messages:,}", inline=True)
        embed.add_field(name="🎤 Minutes vocales/jour", value=f"{avg_voice:,}", inline=True)
        embed.add_field(name="👍 Réactions/jour", value=f"{avg_reactions:,}", inline=True)
        
        # Jour le plus actif
        if total_messages > 0:
            most_active_index = message_data.index(max(message_data))
            most_active_date = date_range[most_active_index]
            most_active_formatted = datetime.datetime.strptime(most_active_date, '%Y-%m-%d').strftime('%d/%m/%Y')
            embed.add_field(
                name="📅 Jour le plus actif",
                value=f"{most_active_formatted} ({message_data[most_active_index]:,} messages)",
                inline=False
            )
        
        embed.set_footer(text=f"Période: {datetime.datetime.strptime(date_range[0], '%Y-%m-%d').strftime('%d/%m/%Y')} - {datetime.datetime.strptime(date_range[-1], '%Y-%m-%d').strftime('%d/%m/%Y')}")
        
        await ctx.send(embed=embed)
    
    @analytics_group.command(name="channels")
    @commands.has_permissions(administrator=True)
    async def analytics_channels_cmd(self, ctx, limit: typing.Optional[int] = 10):
        """
        Affiche les canaux les plus actifs du serveur.
        
        Exemple:
        !analytics channels 5
        """
        if limit < 1 or limit > 25:
            return await ctx.send("❌ La limite doit être comprise entre 1 et 25.")
        
        channels = [(channel_id, count) for channel_id, count in self.channel_activity.items()]
        channels.sort(key=lambda x: x[1], reverse=True)
        
        embed = discord.Embed(
            title=f"📊 Canaux les plus actifs - {ctx.guild.name}",
            color=discord.Color.blue()
        )
        
        for i, (channel_id, count) in enumerate(channels[:limit], 1):
            channel = self.bot.get_channel(channel_id)
            channel_name = channel.mention if channel else f"Canal inconnu ({channel_id})"
            embed.add_field(
                name=f"{i}. {channel_name}",
                value=f"{count:,} messages",
                inline=False
            )
        
        if not channels:
            embed.description = "Aucune donnée d'activité disponible pour les canaux."
        
        await ctx.send(embed=embed)
    
    @analytics_group.command(name="emojis")
    @commands.has_permissions(administrator=True)
    async def analytics_emojis_cmd(self, ctx, limit: typing.Optional[int] = 10):
        """
        Affiche les emojis les plus utilisés sur le serveur.
        
        Exemple:
        !analytics emojis 5
        """
        if limit < 1 or limit > 25:
            return await ctx.send("❌ La limite doit être comprise entre 1 et 25.")
        
        top_emojis = self.emoji_usage.most_common(limit)
        
        embed = discord.Embed(
            title=f"📊 Emojis les plus utilisés - {ctx.guild.name}",
            color=discord.Color.blue()
        )
        
        for i, (emoji, count) in enumerate(top_emojis, 1):
            embed.add_field(
                name=f"{i}. {emoji}",
                value=f"{count:,} utilisations",
                inline=True
            )
        
        if not top_emojis:
            embed.description = "Aucune donnée d'utilisation d'emoji disponible."
        
        await ctx.send(embed=embed)
    
    @analytics_group.command(name="hours")
    @commands.has_permissions(administrator=True)
    async def analytics_hours_cmd(self, ctx):
        """Affiche les heures les plus actives du serveur."""
        hours = [(hour, count) for hour, count in self.active_hour_data.items()]
        hours.sort(key=lambda x: x[0])  # Trier par heure
        
        # Trouver l'heure la plus active
        most_active_hour = max(hours, key=lambda x: x[1]) if hours else (0, 0)
        
        embed = discord.Embed(
            title=f"📊 Heures d'activité - {ctx.guild.name}",
            description=f"Heure la plus active: **{most_active_hour[0]:02d}:00 UTC** ({most_active_hour[1]:,} messages)",
            color=discord.Color.blue()
        )
        
        # Créer une représentation textuelle
        hour_blocks = []
        if hours:
            max_count = max([count for _, count in hours])
            for hour, count in hours:
                if max_count > 0:
                    # Calculer la proportion pour la visualisation
                    proportion = count / max_count
                    num_blocks = round(proportion * 10)
                    bar = '█' * num_blocks + '░' * (10 - num_blocks)
                    hour_blocks.append(f"`{hour:02d}:00` {bar} {count:,}")
        
        # Divisez les heures en deux colonnes
        half = len(hour_blocks) // 2 + len(hour_blocks) % 2
        first_half = '\n'.join(hour_blocks[:half]) if hour_blocks else "Aucune donnée"
        second_half = '\n'.join(hour_blocks[half:]) if hour_blocks and len(hour_blocks) > half else "Suite..."
        
        embed.add_field(name="Heures (UTC) - Partie 1", value=first_half, inline=True)
        if second_half != "Suite...":
            embed.add_field(name="Heures (UTC) - Partie 2", value=second_half, inline=True)
        
        await ctx.send(embed=embed)
    
    @analytics_group.command(name="retention")
    @commands.has_permissions(administrator=True)
    async def analytics_retention_cmd(self, ctx, days: typing.Optional[int] = 30):
        """
        Affiche les statistiques de rétention des membres.
        
        Exemple:
        !analytics retention 60
        """
        if days < 7 or days > 90:
            return await ctx.send("❌ Le nombre de jours doit être compris entre 7 et 90.")
        
        # Calculer les dates
        today = datetime.datetime.utcnow()
        start_date = today - datetime.timedelta(days=days)
        
        # Filtrer les données
        joins = [data for data in self.user_join_data 
                if data.get('timestamp') and data['timestamp'] >= start_date]
        leaves = [data for data in self.user_leave_data 
                 if data.get('timestamp') and data['timestamp'] >= start_date]
        
        total_joins = len(joins)
        total_leaves = len(leaves)
        net_change = total_joins - total_leaves
        
        embed = discord.Embed(
            title=f"📊 Statistiques de rétention - {ctx.guild.name}",
            description=f"Période: {start_date.strftime('%d/%m/%Y')} - {today.strftime('%d/%m/%Y')}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="👋 Nouveaux membres", value=f"{total_joins:,}", inline=True)
        embed.add_field(name="🚶 Départs", value=f"{total_leaves:,}", inline=True)
        embed.add_field(name="📊 Changement net", 
                       value=f"{'+' if net_change >= 0 else ''}{net_change:,}", 
                       inline=True)
        
        # Calculer le taux de rétention
        if total_joins > 0:
            retention_rate = (total_joins - total_leaves) / total_joins * 100
            embed.add_field(
                name="🔄 Taux de rétention",
                value=f"{max(0, retention_rate):.2f}%",
                inline=True
            )
        
        # Moyenne par jour
        avg_joins = round(total_joins / days, 2)
        avg_leaves = round(total_leaves / days, 2)
        
        embed.add_field(name="📈 Nouveaux/jour", value=f"{avg_joins:.2f}", inline=True)
        embed.add_field(name="📉 Départs/jour", value=f"{avg_leaves:.2f}", inline=True)
        
        # Projection sur 30 jours
        if days != 30:
            projected_gain = round((avg_joins - avg_leaves) * 30)
            embed.add_field(
                name="🔮 Projection sur 30 jours",
                value=f"{'+' if projected_gain >= 0 else ''}{projected_gain:,} membres",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Ajoute le cog d'analytique au bot."""
    await bot.add_cog(ServerAnalytics(bot))