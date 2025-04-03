"""
Module de gestion musicale pour LeSéminaire[BOT].
Fournit des commandes pour la lecture de musique dans les salons vocaux,
la gestion des playlists et le partage de samples.
"""
import asyncio
import discord
from discord.ext import commands
import yt_dlp
import logging
import re
from typing import Dict, List, Optional, Union
from database import db_manager
from models import ResourceCategory

# Configuration des logs
logger = logging.getLogger(__name__)

# Options pour yt-dlp
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# Classes pour la gestion de la musique
class YTDLSource(discord.PCMVolumeTransformer):
    """Source audio YouTube pour le bot"""
    
    ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
    
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.webpage_url = data.get('webpage_url')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')
        self.requester = None
    
    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, requester=None):
        """Crée une source audio à partir d'une URL"""
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: cls.ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            # Prendre le premier élément d'une playlist
            data = data['entries'][0]
        
        source = await discord.FFmpegOpusAudio.from_probe(data['url'], **FFMPEG_OPTIONS)
        audio_source = cls(source, data=data)
        audio_source.requester = requester
        return audio_source
    
    @staticmethod
    def parse_duration(duration: int) -> str:
        """Convertit la durée en secondes en format lisible (HH:MM:SS)"""
        if not duration:
            return "Durée inconnue"
        
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

class MusicQueue:
    """Gestionnaire de file d'attente musicale pour un serveur"""
    
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.queue = asyncio.Queue()
        self.current = None
        self.now_playing_message = None
        self.volume = 0.5
        self.loop = False
    
    async def add(self, item):
        """Ajoute un élément à la file d'attente"""
        await self.queue.put(item)
    
    async def get(self):
        """Récupère le prochain élément de la file d'attente"""
        if self.loop and self.current:
            return self.current
        
        if self.queue.empty():
            return None
        
        item = await self.queue.get()
        self.current = item
        return item
    
    def clear(self):
        """Vide la file d'attente"""
        self.queue = asyncio.Queue()
    
    def is_empty(self):
        """Vérifie si la file d'attente est vide"""
        return self.queue.empty() and self.current is None
    
    async def get_queue_list(self) -> List[dict]:
        """Récupère la liste des éléments dans la file d'attente"""
        queue_list = []
        if self.current:
            queue_list.append({
                'title': self.current.title,
                'url': self.current.webpage_url,
                'duration': self.current.duration,
                'requester': self.current.requester,
                'current': True
            })
        
        # Copier les éléments de la queue sans les retirer
        queue_copy = self.queue._queue.copy()
        for item in queue_copy:
            queue_list.append({
                'title': item.title,
                'url': item.webpage_url,
                'duration': item.duration,
                'requester': item.requester,
                'current': False
            })
        
        return queue_list

class MusicCog(commands.Cog):
    """Cog pour la gestion musicale"""
    
    def __init__(self, bot):
        self.bot = bot
        self.queues: Dict[int, MusicQueue] = {}
        self.vc_locks: Dict[int, asyncio.Lock] = {}
    
    def get_queue(self, guild_id: int) -> MusicQueue:
        """Récupère ou crée une file d'attente pour un serveur"""
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue(guild_id)
        return self.queues[guild_id]
    
    def get_lock(self, guild_id: int) -> asyncio.Lock:
        """Récupère ou crée un verrou pour un serveur"""
        if guild_id not in self.vc_locks:
            self.vc_locks[guild_id] = asyncio.Lock()
        return self.vc_locks[guild_id]
    
    async def connect_to_voice(self, ctx) -> Optional[discord.VoiceClient]:
        """
        Connecte le bot à un salon vocal.
        Renvoie None si la connexion échoue.
        """
        if ctx.author.voice is None:
            await ctx.send("❌ Vous devez être dans un salon vocal pour utiliser cette commande.")
            return None
        
        voice_channel = ctx.author.voice.channel
        voice_client = ctx.voice_client
        
        if voice_client is None:
            try:
                voice_client = await voice_channel.connect()
                await ctx.send(f"🔊 Connecté à **{voice_channel.name}**")
            except Exception as e:
                logger.error(f"Erreur lors de la connexion au salon vocal: {e}")
                await ctx.send("❌ Impossible de se connecter au salon vocal.")
                return None
        elif voice_client.channel.id != voice_channel.id:
            await voice_client.move_to(voice_channel)
            await ctx.send(f"🔊 Déplacé vers **{voice_channel.name}**")
        
        return voice_client
    
    async def play_next(self, guild, voice_client):
        """Lit le prochain morceau de la file d'attente"""
        queue = self.get_queue(guild.id)
        
        # Si un message "now playing" existe, le supprimer
        if queue.now_playing_message:
            try:
                await queue.now_playing_message.delete()
            except (discord.NotFound, discord.Forbidden):
                pass
            queue.now_playing_message = None
        
        if voice_client is None or not voice_client.is_connected():
            return
        
        # Attendre que la voix ne soit plus en train de jouer
        while voice_client.is_playing():
            await asyncio.sleep(1)
        
        # Vérifier si le bot a été déconnecté manuellement
        if not voice_client.is_connected():
            return
        
        # Récupérer et jouer le prochain morceau
        source = await queue.get()
        if source is None:
            # File d'attente vide, déconnecter après un délai d'inactivité
            await asyncio.sleep(300)  # 5 minutes
            if not voice_client.is_playing() and queue.is_empty():
                await voice_client.disconnect()
            return
        
        voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(
            self.play_next(guild, voice_client), self.bot.loop
        ).result())
        
        # Enregistrer dans la base de données
        if source.requester and source.webpage_url:
            async with self.get_lock(guild.id):
                db_manager.add_playlist_entry(
                    url=source.webpage_url,
                    added_by=str(source.requester.id),
                    guild_id=str(guild.id),
                    title=source.title,
                    duration=source.duration
                )
        
        # Trouver un canal pour envoyer le message "now playing"
        guild_settings = db_manager.get_guild_settings(str(guild.id))
        if guild_settings and guild_settings.music_channel_id:
            try:
                channel = self.bot.get_channel(int(guild_settings.music_channel_id))
            except (ValueError, AttributeError):
                channel = None
        else:
            # Trouve le premier canal de texte où le bot peut écrire
            channel = next((
                c for c in guild.text_channels
                if c.permissions_for(guild.me).send_messages
            ), None)
        
        if channel:
            embed = discord.Embed(
                title="🎵 En cours de lecture",
                description=f"**{source.title}**",
                color=0xe74c3c,
                url=source.webpage_url
            )
            
            embed.add_field(
                name="Durée",
                value=YTDLSource.parse_duration(source.duration),
                inline=True
            )
            
            if source.requester:
                embed.add_field(
                    name="Demandé par",
                    value=source.requester.mention,
                    inline=True
                )
            
            if source.thumbnail:
                embed.set_thumbnail(url=source.thumbnail)
            
            embed.set_footer(text=f"Le Séminaire - Système musical | Volume: {int(queue.volume * 100)}%")
            
            try:
                queue.now_playing_message = await channel.send(embed=embed)
            except discord.Forbidden:
                pass
    
    @commands.command(name="join", aliases=["j", "rejoindre"])
    async def join(self, ctx):
        """
        Rejoint le salon vocal de l'utilisateur.
        
        Exemple: !join
        """
        await self.connect_to_voice(ctx)
    
    @commands.command(name="play", aliases=["p", "jouer"])
    async def play(self, ctx, *, query: str):
        """
        Joue de la musique depuis YouTube.
        
        Exemple: !play https://www.youtube.com/watch?v=dQw4w9WgXcQ
        Ou: !play rickroll
        """
        async with ctx.typing():
            voice_client = await self.connect_to_voice(ctx)
            if voice_client is None:
                return
            
            # Détecter si c'est une URL ou une recherche
            if not (query.startswith('http://') or query.startswith('https://')):
                query = f"ytsearch:{query}"
            
            # Récupérer la source audio
            try:
                source = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True, requester=ctx.author)
            except Exception as e:
                await ctx.send(f"❌ Erreur lors de la récupération de l'audio: {str(e)}")
                logger.error(f"Erreur yt-dlp: {e}")
                return
            
            # Ajouter à la file d'attente
            queue = self.get_queue(ctx.guild.id)
            await queue.add(source)
            
            await ctx.send(f"🎵 Ajouté à la file d'attente: **{source.title}**")
            
            # Si aucune musique n'est en cours, lancer la lecture
            if not voice_client.is_playing():
                await self.play_next(ctx.guild, voice_client)
    
    @commands.command(name="music_pause", aliases=["pausemusic", "mpause", "marreter"])
    async def music_pause(self, ctx):
        """
        Met en pause la lecture musicale en cours.
        
        Exemple: !music_pause
        """
        voice_client = ctx.voice_client
        if voice_client is None:
            await ctx.send("❌ Le bot n'est pas connecté à un salon vocal.")
            return
        
        if voice_client.is_playing():
            voice_client.pause()
            await ctx.send("⏸️ Lecture mise en pause.")
        else:
            await ctx.send("❌ Aucune lecture en cours.")
    
    @commands.command(name="resume", aliases=["reprendre", "continuer"])
    async def resume(self, ctx):
        """
        Reprend la lecture mise en pause.
        
        Exemple: !resume
        """
        voice_client = ctx.voice_client
        if voice_client is None:
            await ctx.send("❌ Le bot n'est pas connecté à un salon vocal.")
            return
        
        if voice_client.is_paused():
            voice_client.resume()
            await ctx.send("▶️ Lecture reprise.")
        else:
            await ctx.send("❌ La lecture n'est pas en pause.")
    
    @commands.command(name="skip", aliases=["s", "passer"])
    async def skip(self, ctx):
        """
        Passe au morceau suivant dans la file d'attente.
        
        Exemple: !skip
        """
        voice_client = ctx.voice_client
        if voice_client is None:
            await ctx.send("❌ Le bot n'est pas connecté à un salon vocal.")
            return
        
        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()
            await ctx.send("⏭️ Passage au morceau suivant...")
        else:
            await ctx.send("❌ Aucune lecture en cours.")
    
    @commands.command(name="queue", aliases=["q", "liste", "file"])
    async def queue(self, ctx):
        """
        Affiche la file d'attente musicale.
        
        Exemple: !queue
        """
        queue = self.get_queue(ctx.guild.id)
        queue_list = await queue.get_queue_list()
        
        if not queue_list:
            await ctx.send("📭 La file d'attente est vide.")
            return
        
        embed = discord.Embed(
            title="🎵 File d'attente musicale",
            description="Voici les morceaux en attente de lecture :",
            color=0x9b59b6
        )
        
        total_duration = 0
        for i, item in enumerate(queue_list):
            if item.get('current'):
                title = f"🎧 **En cours**: {item['title']}"
            else:
                title = f"{i}. {item['title']}"
            
            duration = YTDLSource.parse_duration(item['duration'])
            requester = item.get('requester')
            requester_mention = requester.mention if requester else "Inconnu"
            
            embed.add_field(
                name=title,
                value=f"Durée: {duration} | Demandé par: {requester_mention}",
                inline=False
            )
            
            if item['duration']:
                total_duration += item['duration']
        
        embed.set_footer(text=f"Total: {len(queue_list)} morceaux | Durée totale: {YTDLSource.parse_duration(total_duration)}")
        await ctx.send(embed=embed)
    
    @commands.command(name="clear", aliases=["vider", "nettoyer"])
    async def clear(self, ctx):
        """
        Vide la file d'attente musicale.
        
        Exemple: !clear
        """
        queue = self.get_queue(ctx.guild.id)
        queue.clear()
        await ctx.send("🧹 La file d'attente a été vidée.")
    
    @commands.command(name="volume", aliases=["vol", "v"])
    async def volume(self, ctx, volume: int = None):
        """
        Affiche ou modifie le volume de la lecture (0-100).
        
        Exemple: !volume 75
        """
        queue = self.get_queue(ctx.guild.id)
        voice_client = ctx.voice_client
        
        if volume is None:
            await ctx.send(f"🔊 Volume actuel : **{int(queue.volume * 100)}%**")
            return
        
        if not 0 <= volume <= 100:
            await ctx.send("❌ Le volume doit être entre 0 et 100.")
            return
        
        queue.volume = volume / 100
        if voice_client and voice_client.source:
            voice_client.source.volume = queue.volume
        
        await ctx.send(f"🔊 Volume réglé à **{volume}%**")
    
    @commands.command(name="now", aliases=["np", "nowplaying", "encours"])
    async def now_playing(self, ctx):
        """
        Affiche le morceau en cours de lecture.
        
        Exemple: !now
        """
        voice_client = ctx.voice_client
        if voice_client is None or not (voice_client.is_playing() or voice_client.is_paused()):
            await ctx.send("❌ Aucune lecture en cours.")
            return
        
        queue = self.get_queue(ctx.guild.id)
        if not queue.current:
            await ctx.send("❌ Aucune information sur le morceau en cours.")
            return
        
        source = queue.current
        status = "⏸️ En pause" if voice_client.is_paused() else "🎵 En cours de lecture"
        
        embed = discord.Embed(
            title=status,
            description=f"**{source.title}**",
            color=0xe74c3c,
            url=source.webpage_url
        )
        
        embed.add_field(
            name="Durée",
            value=YTDLSource.parse_duration(source.duration),
            inline=True
        )
        
        embed.add_field(
            name="Volume",
            value=f"{int(queue.volume * 100)}%",
            inline=True
        )
        
        if source.requester:
            embed.add_field(
                name="Demandé par",
                value=source.requester.mention,
                inline=True
            )
        
        if source.thumbnail:
            embed.set_thumbnail(url=source.thumbnail)
        
        embed.set_footer(text="Le Séminaire - Système musical")
        await ctx.send(embed=embed)
    
    @commands.command(name="loop", aliases=["boucle", "repeat"])
    async def loop(self, ctx):
        """
        Active/désactive la lecture en boucle du morceau actuel.
        
        Exemple: !loop
        """
        queue = self.get_queue(ctx.guild.id)
        queue.loop = not queue.loop
        
        status = "activée" if queue.loop else "désactivée"
        await ctx.send(f"🔁 Lecture en boucle {status}.")
    
    @commands.command(name="disconnect", aliases=["dc", "leave", "quitter"])
    async def disconnect(self, ctx):
        """
        Déconnecte le bot du salon vocal.
        
        Exemple: !disconnect
        """
        voice_client = ctx.voice_client
        if voice_client is None:
            await ctx.send("❌ Le bot n'est pas connecté à un salon vocal.")
            return
        
        queue = self.get_queue(ctx.guild.id)
        queue.clear()
        queue.current = None
        
        await voice_client.disconnect()
        await ctx.send("👋 Déconnecté du salon vocal.")
    
    @commands.command(name="sample", aliases=["samples", "son"])
    async def sample(self, ctx, subcommand=None, *, args=None):
        """
        Gère les samples musicaux de la communauté.
        
        Exemple: !sample add "Sample de batterie" https://example.com/sample.mp3 Drums "Sample de batterie lourd et puissant"
        """
        if subcommand is None:
            embed = discord.Embed(
                title="🎧 Commandes de Samples",
                description="Voici les commandes disponibles pour gérer les samples :",
                color=0x3498db
            )
            
            embed.add_field(
                name="!sample add <titre> <url> [genre] [description] [bpm] [key]",
                value="Ajoute un nouveau sample musical",
                inline=False
            )
            
            embed.add_field(
                name="!sample list",
                value="Liste les samples disponibles",
                inline=False
            )
            
            embed.add_field(
                name="!sample search <terme>",
                value="Recherche des samples par mot-clé",
                inline=False
            )
            
            embed.set_footer(text="Le Séminaire - Système de partage de samples")
            await ctx.send(embed=embed)
            return
        
        if subcommand.lower() == "add":
            if args is None:
                await ctx.send("❌ Format incorrect. Utilisez `!sample add <titre> <url> [genre] [description] [bpm] [key]`")
                return
            
            # Extraction des arguments
            match = re.match(r'"([^"]+)"\s+(\S+)(?:\s+([^"\s]+))?(?:\s+"([^"]+)")?(?:\s+(\d+))?(?:\s+([A-G][#b]?m?))?', args)
            if not match:
                await ctx.send("❌ Format incorrect. Utilisez `!sample add \"Titre\" URL [Genre] \"Description\" [BPM] [Key]`")
                return
            
            title, url, genre, description, bpm, key = match.groups()
            
            if bpm:
                bpm = int(bpm)
            
            # Ajouter le sample à la base de données
            sample = db_manager.add_music_sample(
                title=title,
                url=url,
                added_by=str(ctx.author.id),
                description=description,
                bpm=bpm,
                key=key,
                genre=genre
            )
            
            embed = discord.Embed(
                title="✅ Sample ajouté",
                description=f"Le sample **{title}** a été ajouté avec succès !",
                color=0x2ecc71
            )
            
            if genre:
                embed.add_field(name="Genre", value=genre, inline=True)
            if bpm:
                embed.add_field(name="BPM", value=bpm, inline=True)
            if key:
                embed.add_field(name="Tonalité", value=key, inline=True)
            if description:
                embed.add_field(name="Description", value=description, inline=False)
            
            embed.add_field(name="URL", value=url, inline=False)
            embed.set_footer(text=f"Ajouté par {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
        
        elif subcommand.lower() == "list":
            # Récupérer les samples
            samples = db_manager.get_music_samples(limit=20)
            
            if not samples:
                await ctx.send("📭 Aucun sample trouvé. Utilisez `!sample add` pour ajouter des samples.")
                return
            
            embed = discord.Embed(
                title="🎧 Samples Musicaux",
                description="Voici les samples disponibles :",
                color=0x3498db
            )
            
            for i, sample in enumerate(samples, start=1):
                details = []
                if sample.genre:
                    details.append(f"Genre: {sample.genre}")
                if sample.bpm:
                    details.append(f"BPM: {sample.bpm}")
                if sample.key:
                    details.append(f"Tonalité: {sample.key}")
                
                details_str = " | ".join(details) if details else "Aucun détail"
                description = sample.description or "Aucune description"
                
                embed.add_field(
                    name=f"{i}. {sample.title}",
                    value=f"{description}\n{details_str}\n[Lien]({sample.url})",
                    inline=False
                )
            
            embed.set_footer(text=f"Total: {len(samples)} samples")
            await ctx.send(embed=embed)
        
        elif subcommand.lower() == "search":
            if not args:
                await ctx.send("❌ Veuillez spécifier un terme de recherche. Exemple: `!sample search drums`")
                return
            
            # Rechercher les samples
            samples = db_manager.search_music_samples(args)
            
            if not samples:
                await ctx.send(f"❌ Aucun sample trouvé pour '{args}'.")
                return
            
            embed = discord.Embed(
                title=f"🎧 Recherche de Samples: {args}",
                description=f"Résultats de recherche pour '{args}' :",
                color=0x3498db
            )
            
            for i, sample in enumerate(samples, start=1):
                details = []
                if sample.genre:
                    details.append(f"Genre: {sample.genre}")
                if sample.bpm:
                    details.append(f"BPM: {sample.bpm}")
                if sample.key:
                    details.append(f"Tonalité: {sample.key}")
                
                details_str = " | ".join(details) if details else "Aucun détail"
                description = sample.description or "Aucune description"
                
                embed.add_field(
                    name=f"{i}. {sample.title}",
                    value=f"{description}\n{details_str}\n[Lien]({sample.url})",
                    inline=False
                )
            
            embed.set_footer(text=f"Total: {len(samples)} résultats")
            await ctx.send(embed=embed)
        
        else:
            await ctx.send("❌ Sous-commande non reconnue. Utilisez `!sample` pour voir les commandes disponibles.")
    
    # Événements
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Gère les changements d'état vocal"""
        if member.id == self.bot.user.id and before.channel and not after.channel:
            # Le bot a été déconnecté du salon vocal
            guild_id = before.channel.guild.id
            if guild_id in self.queues:
                queue = self.queues[guild_id]
                queue.clear()
                queue.current = None

# Fonction d'installation du cog
async def setup(bot):
    await bot.add_cog(MusicCog(bot))