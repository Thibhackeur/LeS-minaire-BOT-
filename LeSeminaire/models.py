"""
Module de définition des modèles de données pour LeSéminaire[BOT].
Contient les classes de modèles SQLAlchemy pour interagir avec la base de données.
"""
import enum
import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship

# Utilisation de la base SQLAlchemy définie dans app.py
Base = db.Model

class ResourceCategory(enum.Enum):
    """Énumération des catégories de ressources artistiques"""
    GENERAL = "Général"
    AUDIO = "Audio"
    PRODUCTION = "Production"
    MIXING = "Mixage"
    MASTERING = "Mastering"
    VIDEO = "Vidéo"
    PHOTO = "Photographie"
    GRAPHIC = "Graphisme"
    BUSINESS = "Business"
    LEGAL = "Juridique"

class Resource(Base):
    """Modèle pour les ressources artistiques partagées"""
    __tablename__ = 'resources'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Enum(ResourceCategory), default=ResourceCategory.GENERAL)
    tags = Column(String(200), nullable=True)
    added_by = Column(String(100), nullable=True)  # ID Discord ou nom d'utilisateur
    added_at = Column(DateTime, default=datetime.datetime.utcnow)
    approved = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Resource '{self.title}' ({self.category.value})>"

class MusicSample(Base):
    """Modèle pour les samples musicaux partagés"""
    __tablename__ = 'music_samples'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)  # URL de stockage ou d'accès au sample
    description = Column(Text, nullable=True)
    bpm = Column(Integer, nullable=True)
    key = Column(String(10), nullable=True)  # Tonalité musicale
    genre = Column(String(50), nullable=True)
    tags = Column(String(200), nullable=True)
    duration = Column(Integer, nullable=True)  # Durée en secondes
    added_by = Column(String(100), nullable=False)  # ID Discord
    added_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<MusicSample '{self.title}' by {self.added_by}>"

class Collaboration(Base):
    """Modèle pour les projets de collaboration entre artistes"""
    __tablename__ = 'collaborations'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="En cours")  # En cours, Terminé, Abandonné
    created_by = Column(String(100), nullable=False)  # ID Discord
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relations
    members = relationship("CollaborationMember", back_populates="collaboration", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Collaboration '{self.title}' ({self.status})>"

class CollaborationMember(Base):
    """Modèle pour les membres d'un projet de collaboration"""
    __tablename__ = 'collaboration_members'
    
    id = Column(Integer, primary_key=True)
    collaboration_id = Column(Integer, ForeignKey('collaborations.id'), nullable=False)
    member_id = Column(String(100), nullable=False)  # ID Discord
    role = Column(String(50), nullable=True)  # Rôle dans la collaboration
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relations
    collaboration = relationship("Collaboration", back_populates="members")
    
    def __repr__(self):
        return f"<CollaborationMember {self.member_id} in {self.collaboration_id}>"

class PlaylistEntry(Base):
    """Modèle pour les entrées de la liste de lecture musicale"""
    __tablename__ = 'playlist_entries'
    
    id = Column(Integer, primary_key=True)
    url = Column(String(500), nullable=False)  # URL YouTube ou autre
    title = Column(String(200), nullable=True)
    duration = Column(Integer, nullable=True)  # Durée en secondes
    added_by = Column(String(100), nullable=False)  # ID Discord
    guild_id = Column(String(100), nullable=False)  # ID du serveur Discord
    added_at = Column(DateTime, default=datetime.datetime.utcnow)
    played_at = Column(DateTime, nullable=True)  # Timestamp de la dernière lecture
    
    def __repr__(self):
        return f"<PlaylistEntry '{self.title}' by {self.added_by}>"

class GuildSettings(Base):
    """Modèle pour les paramètres personnalisés par serveur"""
    __tablename__ = 'guild_settings'
    
    guild_id = Column(String(100), primary_key=True)  # ID du serveur Discord
    prefix = Column(String(10), default='!')  # Préfixe personnalisé pour les commandes
    welcome_channel_id = Column(String(100), nullable=True)
    rules_channel_id = Column(String(100), nullable=True)
    verification_enabled = Column(Boolean, default=True)
    music_channel_id = Column(String(100), nullable=True)
    dj_role_id = Column(String(100), nullable=True)  # Rôle autorisé à contrôler le bot musical
    resource_channel_id = Column(String(100), nullable=True)
    max_playlist_length = Column(Integer, default=20)  # Nombre max d'items dans la playlist
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<GuildSettings for {self.guild_id}>"


class Admin(Base, UserMixin):
    """Modèle pour les administrateurs du site web"""
    __tablename__ = 'admins'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    def set_password(self, password):
        """Définit le mot de passe haché"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Vérifie si le mot de passe est correct"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f"<Admin {self.username}>"


class ContactMessage(Base):
    """Modèle pour les messages de contact"""
    __tablename__ = 'contact_messages'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), nullable=False)
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    discord_username = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_read = Column(Boolean, default=False)
    responded = Column(Boolean, default=False)
    responded_at = Column(DateTime, nullable=True)
    response_text = Column(Text, nullable=True)
    priority = Column(Integer, default=0)  # 0=Normal, 1=Medium, 2=High
    
    def __repr__(self):
        return f"<ContactMessage from {self.name} ({self.subject})>"


class CommandStat(Base):
    """Modèle pour les statistiques des commandes"""
    __tablename__ = 'command_stats'
    
    id = Column(Integer, primary_key=True)
    command_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=True)
    guild_id = Column(String(100), nullable=False)  # ID du serveur Discord
    user_id = Column(String(100), nullable=False)  # ID Discord
    used_at = Column(DateTime, default=datetime.datetime.utcnow)
    success = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<CommandStat {self.command_name} by {self.user_id}>"


class AdminSettings(Base):
    """Modèle pour les paramètres d'administration"""
    __tablename__ = 'admin_settings'
    
    id = Column(Integer, primary_key=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<AdminSettings {self.setting_key}>"


class MessagePreference(Base):
    """Modèle pour les préférences de messagerie directe des utilisateurs"""
    __tablename__ = 'message_preferences'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), unique=True, nullable=False)  # ID Discord
    opt_out = Column(Boolean, default=False)  # True si l'utilisateur a désactivé les DMs
    last_dm = Column(DateTime, nullable=True)  # Dernière fois que l'utilisateur a reçu un DM
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        status = "désactivés" if self.opt_out else "activés"
        return f"<MessagePreference {self.user_id} (DMs {status})>"


class ServerStat(Base):
    """Modèle pour les statistiques des serveurs Discord"""
    __tablename__ = 'server_stats'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    guild_id = Column(String(100), nullable=True)  # ID du serveur Discord
    type = Column(String(50), nullable=False)  # Type de statistique: 'hourly', 'daily', 'weekly'
    data = Column(Text, nullable=True)  # Données JSON encodées
    
    def __repr__(self):
        return f"<ServerStat {self.type} {self.timestamp.strftime('%Y-%m-%d %H:%M')}>"


class ChannelStat(Base):
    """Modèle pour les statistiques des canaux Discord"""
    __tablename__ = 'channel_stats'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    guild_id = Column(String(100), nullable=False)  # ID du serveur Discord
    channel_id = Column(String(100), nullable=False)  # ID du canal Discord
    channel_name = Column(String(100), nullable=True)  # Nom du canal (pour référence facile)
    message_count = Column(Integer, default=0)  # Nombre de messages
    user_count = Column(Integer, default=0)  # Nombre d'utilisateurs uniques
    
    def __repr__(self):
        return f"<ChannelStat {self.channel_name or self.channel_id} ({self.message_count} messages)>"


class UserStat(Base):
    """Modèle pour les statistiques des utilisateurs Discord"""
    __tablename__ = 'user_stats'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    guild_id = Column(String(100), nullable=False)  # ID du serveur Discord
    user_id = Column(String(100), nullable=False)  # ID Discord
    username = Column(String(100), nullable=True)  # Nom d'utilisateur (pour référence facile)
    message_count = Column(Integer, default=0)  # Nombre de messages
    voice_minutes = Column(Integer, default=0)  # Minutes en vocal
    reaction_count = Column(Integer, default=0)  # Nombre de réactions
    
    def __repr__(self):
        return f"<UserStat {self.username or self.user_id} ({self.message_count} messages)>"


class EngagementData(Base):
    """Modèle pour les données d'engagement du serveur"""
    __tablename__ = 'engagement_data'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    guild_id = Column(String(100), nullable=False)  # ID du serveur Discord
    total_members = Column(Integer, default=0)  # Nombre total de membres
    online_members = Column(Integer, default=0)  # Nombre de membres en ligne
    active_members = Column(Integer, default=0)  # Nombre de membres actifs (qui ont envoyé un message)
    messages_sent = Column(Integer, default=0)  # Nombre de messages envoyés
    reactions_added = Column(Integer, default=0)  # Nombre de réactions ajoutées
    voice_connections = Column(Integer, default=0)  # Nombre de connexions vocales
    voice_minutes = Column(Integer, default=0)  # Minutes totales en vocal
    
    def __repr__(self):
        return f"<EngagementData {self.timestamp.strftime('%Y-%m-%d %H:%M')} ({self.active_members}/{self.total_members} membres actifs)>"