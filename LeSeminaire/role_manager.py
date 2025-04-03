"""
Module de gestion des rôles artistiques.
Permet de créer et gérer un système de rôles par réaction pour
les différentes spécialités artistiques des membres du Séminaire.
"""

import discord
import logging
from typing import Dict, List, Tuple, Optional, Set, Union

# Configuration du logger
logger = logging.getLogger('role_manager')

# Mapping des emojis aux rôles artistiques
DEFAULT_ROLE_EMOJI_MAPPING = {
    '🎧': 'Ingé son',     # Ingénieur du son
    '🥁': 'Beatmaker',    # Producteur de beats
    '🎤': 'Rappeur',      # Rappeur/MC
    '🎸': 'Musicien',     # Musicien
    '🎥': 'Vidéaste',     # Vidéaste
    '📸': 'Photographe',  # Photographe
    '🎨': 'Graphiste',    # Designer graphique
    '🖋️': 'Auteur',       # Auteur/parolier
    '🎭': 'Performer',    # Performeur/artiste scénique
    '🎹': 'Compositeur',  # Compositeur
    '🎬': 'Réalisateur',  # Réalisateur
    '🎻': 'Instrumentiste', # Instrumentiste
}

class RoleManager:
    """
    Gestionnaire de rôles artistiques pour le serveur Le Séminaire.
    """
    
    def __init__(self, bot):
        """
        Initialise le gestionnaire de rôles.
        
        Args:
            bot: L'instance du bot Discord
        """
        self.bot = bot
        self.role_channels: Dict[int, int] = {}  # guild_id -> channel_id
        self.role_messages: Dict[int, int] = {}  # guild_id -> message_id
        self.role_emoji_mapping: Dict[int, Dict[str, str]] = {}  # guild_id -> {emoji -> role_name}
        
    async def setup_role_menu(self, guild: discord.Guild, channel: discord.TextChannel = None) -> Tuple[bool, str]:
        """
        Configure le menu de sélection des rôles artistiques.
        
        Args:
            guild: Le serveur Discord
            channel: Le canal où créer le menu (optionnel)
            
        Returns:
            Tuple (succès, message)
        """
        try:
            # Si aucun canal n'est spécifié, chercher un canal approprié
            if not channel:
                potential_channels = ['rôles', 'roles', 'role-selection', 'sélection-rôles']
                for channel_name in potential_channels:
                    channel = discord.utils.get(guild.text_channels, name=channel_name)
                    if channel:
                        break
                
                # Si toujours pas de canal, utiliser le canal général
                if not channel:
                    channel = discord.utils.get(guild.text_channels, name='général')
                
                # Si toujours rien, créer un nouveau canal
                if not channel:
                    # Trouver la catégorie INFORMATIONS
                    category = discord.utils.get(guild.categories, name='INFORMATIONS')
                    if not category:
                        category = guild.categories[0] if guild.categories else None
                    
                    # Créer le canal
                    channel = await guild.create_text_channel(
                        name='rôles-artistiques',
                        category=category,
                        topic="Sélectionne tes spécialités artistiques en réagissant aux emojis"
                    )
                    
                    logger.info(f"Canal 'rôles-artistiques' créé dans la catégorie {category.name if category else 'sans catégorie'}")
            
            # Créer les rôles s'ils n'existent pas
            created_roles = []
            for role_name in DEFAULT_ROLE_EMOJI_MAPPING.values():
                role = discord.utils.get(guild.roles, name=role_name)
                if not role:
                    # Générer une couleur basée sur le nom du rôle (pour la diversité)
                    hue = (hash(role_name) % 360) / 360.0
                    rgb = self._hsv_to_rgb(hue, 0.7, 0.9)
                    color = discord.Color.from_rgb(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
                    
                    role = await guild.create_role(
                        name=role_name,
                        color=color,
                        mentionable=True,
                        reason="Création des rôles artistiques"
                    )
                    created_roles.append(role_name)
            
            # Créer le message du menu de rôles
            role_menu_content = self._create_role_menu_content()
            
            # Envoyer le message
            role_message = await channel.send(role_menu_content)
            
            # Ajouter les réactions
            for emoji in DEFAULT_ROLE_EMOJI_MAPPING.keys():
                await role_message.add_reaction(emoji)
            
            # Épingler le message
            await role_message.pin()
            
            # Enregistrer les informations
            self.role_channels[guild.id] = channel.id
            self.role_messages[guild.id] = role_message.id
            self.role_emoji_mapping[guild.id] = DEFAULT_ROLE_EMOJI_MAPPING.copy()
            
            # Message de succès
            if created_roles:
                return True, f"✅ Menu de rôles artistiques créé dans {channel.mention}! Rôles créés: {', '.join(created_roles)}"
            else:
                return True, f"✅ Menu de rôles artistiques créé dans {channel.mention}!"
            
        except Exception as e:
            logger.error(f"Erreur lors de la configuration du menu de rôles: {e}")
            return False, f"❌ Erreur lors de la configuration du menu de rôles: {e}"
    
    def _create_role_menu_content(self) -> str:
        """
        Crée le contenu du message du menu de rôles.
        
        Returns:
            Le contenu formaté du message
        """
        return (
            "# 🎭 Rôles Artistiques\n\n"
            "Sélectionne tes spécialités artistiques en réagissant avec les emojis correspondants :\n\n"
            "## Spécialités Musicales\n"
            "🎤 → **Rappeur** - Pour les MC et artistes vocaux\n"
            "🎹 → **Compositeur** - Pour ceux qui composent la musique\n"
            "🎸 → **Musicien** - Pour les instrumentistes et interprètes\n"
            "🥁 → **Beatmaker** - Pour les producteurs de beats\n"
            "🎧 → **Ingé son** - Pour les ingénieurs et techniciens du son\n"
            "🎻 → **Instrumentiste** - Pour les musiciens classiques et traditionnels\n\n"
            
            "## Spécialités Visuelles\n"
            "🎥 → **Vidéaste** - Pour ceux qui créent du contenu vidéo\n"
            "📸 → **Photographe** - Pour les photographes\n"
            "🎨 → **Graphiste** - Pour les designers graphiques et illustrateurs\n"
            "🎬 → **Réalisateur** - Pour les réalisateurs de clips et films\n\n"
            
            "## Autres Spécialités\n"
            "🖋️ → **Auteur** - Pour les paroliers et écrivains\n"
            "🎭 → **Performer** - Pour les artistes scéniques et performeurs\n\n"
            
            "*Tu peux sélectionner plusieurs rôles. Ils apparaîtront sur ton profil et te permettront "
            "d'être mentionné lors d'annonces spécifiques à ta spécialité.*"
        )
    
    async def handle_role_reaction(self, payload: discord.RawReactionActionEvent, adding: bool = True) -> None:
        """
        Gère les réactions aux messages de sélection de rôles.
        
        Args:
            payload: Les données de l'événement de réaction
            adding: True si la réaction est ajoutée, False si elle est retirée
        """
        # Ignorer les réactions du bot
        if payload.user_id == self.bot.user.id:
            return
        
        guild_id = payload.guild_id
        
        # Vérifier si c'est un message de rôle connu
        if guild_id not in self.role_messages or payload.message_id != self.role_messages[guild_id]:
            return
        
        # Récupérer les informations nécessaires
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        
        member = guild.get_member(payload.user_id)
        if not member:
            return
        
        # Récupérer le rôle correspondant à l'emoji
        emoji = str(payload.emoji)
        if guild_id not in self.role_emoji_mapping or emoji not in self.role_emoji_mapping[guild_id]:
            return
        
        role_name = self.role_emoji_mapping[guild_id][emoji]
        role = discord.utils.get(guild.roles, name=role_name)
        
        if not role:
            logger.warning(f"Rôle '{role_name}' introuvable sur le serveur {guild.name}")
            return
        
        try:
            # Ajouter ou retirer le rôle
            if adding:
                if role not in member.roles:
                    await member.add_roles(role, reason="Sélection de rôle artistique via réaction")
                    logger.info(f"Rôle '{role_name}' ajouté à {member.name} sur {guild.name}")
            else:
                if role in member.roles:
                    await member.remove_roles(role, reason="Désélection de rôle artistique via réaction")
                    logger.info(f"Rôle '{role_name}' retiré de {member.name} sur {guild.name}")
                    
        except Exception as e:
            logger.error(f"Erreur lors de la modification des rôles de {member.name}: {e}")
    
    def _hsv_to_rgb(self, h: float, s: float, v: float) -> Tuple[float, float, float]:
        """
        Convertit une couleur HSV en RGB.
        
        Args:
            h: Teinte (0-1)
            s: Saturation (0-1)
            v: Valeur (0-1)
            
        Returns:
            Tuple RGB (0-1, 0-1, 0-1)
        """
        if s == 0.0:
            return (v, v, v)
        
        i = int(h * 6)
        f = (h * 6) - i
        p = v * (1 - s)
        q = v * (1 - s * f)
        t = v * (1 - s * (1 - f))
        
        if i % 6 == 0:
            return (v, t, p)
        elif i % 6 == 1:
            return (q, v, p)
        elif i % 6 == 2:
            return (p, v, t)
        elif i % 6 == 3:
            return (p, q, v)
        elif i % 6 == 4:
            return (t, p, v)
        else:
            return (v, p, q)