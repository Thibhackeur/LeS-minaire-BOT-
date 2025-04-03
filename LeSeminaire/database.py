"""
Module de gestion de la base de données pour LeSéminaire[BOT].
Fournit des classes et fonctions pour interagir avec la base de données.
"""
import os
import logging
from typing import List, Optional, Dict, Any, Union
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from models import Base, Resource, MusicSample, Collaboration, CollaborationMember
from models import PlaylistEntry, GuildSettings, ResourceCategory

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Gestionnaire de la base de données du bot.
    Fournit des méthodes pour interagir avec les différentes tables.
    """
    
    def __init__(self):
        """Initialise la connexion à la base de données."""
        db_url = os.environ.get('DATABASE_URL', 'sqlite:///le_seminaire.db')
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        self.engine = create_engine(db_url, pool_pre_ping=True)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        
        # Créer les tables si elles n'existent pas
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Tables de base de données créées/vérifiées avec succès.")
        except Exception as e:
            logger.error(f"Erreur lors de la création des tables: {e}")
    
    def get_session(self) -> Session:
        """
        Récupère une session de base de données.
        
        Returns:
            Session SQLAlchemy
        """
        if not self.session or not self.session.is_active:
            self.session = self.Session()
        return self.session
    
    def close(self):
        """Ferme la connexion à la base de données."""
        if self.session:
            self.session.close()
    
    # Méthodes pour les ressources artistiques
    def add_resource(self, title: str, url: str, description: str = None, 
                    category: ResourceCategory = ResourceCategory.GENERAL, 
                    tags: str = None, added_by: str = None) -> Resource:
        """
        Ajoute une nouvelle ressource à la base de données.
        
        Args:
            title: Titre de la ressource
            url: URL de la ressource
            description: Description optionnelle
            category: Catégorie de la ressource
            tags: Tags séparés par des virgules
            added_by: ID Discord ou nom d'utilisateur de l'ajouteur
            
        Returns:
            L'objet Resource créé
        """
        session = self.get_session()
        resource = Resource(
            title=title,
            url=url,
            description=description,
            category=category,
            tags=tags,
            added_by=added_by
        )
        session.add(resource)
        session.commit()
        return resource
    
    def get_resource(self, resource_id: int) -> Optional[Resource]:
        """
        Récupère une ressource par son ID.
        
        Args:
            resource_id: ID de la ressource
            
        Returns:
            L'objet Resource ou None si non trouvé
        """
        session = self.get_session()
        return session.query(Resource).filter(Resource.id == resource_id).first()
    
    def get_resources_by_category(self, category: ResourceCategory) -> List[Resource]:
        """
        Récupère les ressources par catégorie.
        
        Args:
            category: Catégorie de ressources à récupérer
            
        Returns:
            Liste des ressources dans cette catégorie
        """
        session = self.get_session()
        return session.query(Resource).filter(Resource.category == category).all()
    
    def search_resources(self, search_term: str) -> List[Resource]:
        """
        Recherche des ressources par terme de recherche.
        
        Args:
            search_term: Terme à rechercher dans le titre, la description et les tags
            
        Returns:
            Liste des ressources correspondantes
        """
        session = self.get_session()
        search = f"%{search_term}%"
        return session.query(Resource).filter(
            (Resource.title.ilike(search)) | 
            (Resource.description.ilike(search)) | 
            (Resource.tags.ilike(search))
        ).all()
    
    def delete_resource(self, resource_id: int) -> bool:
        """
        Supprime une ressource par son ID.
        
        Args:
            resource_id: ID de la ressource à supprimer
            
        Returns:
            True si la suppression a réussi, False sinon
        """
        session = self.get_session()
        resource = session.query(Resource).filter(Resource.id == resource_id).first()
        if resource:
            session.delete(resource)
            session.commit()
            return True
        return False
    
    # Méthodes pour les samples musicaux
    def add_music_sample(self, title: str, url: str, added_by: str, 
                         description: str = None, bpm: int = None, 
                         key: str = None, genre: str = None, 
                         tags: str = None, duration: int = None) -> MusicSample:
        """
        Ajoute un nouveau sample musical à la base de données.
        
        Args:
            title: Titre du sample
            url: URL d'accès au sample
            added_by: ID Discord de l'ajouteur
            description: Description optionnelle
            bpm: Tempo en BPM
            key: Tonalité musicale
            genre: Genre musical
            tags: Tags séparés par des virgules
            duration: Durée en secondes
            
        Returns:
            L'objet MusicSample créé
        """
        session = self.get_session()
        sample = MusicSample(
            title=title,
            url=url,
            description=description,
            bpm=bpm,
            key=key,
            genre=genre,
            tags=tags,
            duration=duration,
            added_by=added_by
        )
        session.add(sample)
        session.commit()
        return sample
    
    def get_music_samples(self, limit: int = 10) -> List[MusicSample]:
        """
        Récupère les samples musicaux les plus récents.
        
        Args:
            limit: Nombre maximum de samples à récupérer
            
        Returns:
            Liste des samples musicaux
        """
        session = self.get_session()
        return session.query(MusicSample).order_by(desc(MusicSample.added_at)).limit(limit).all()
    
    def search_music_samples(self, search_term: str) -> List[MusicSample]:
        """
        Recherche des samples musicaux par terme de recherche.
        
        Args:
            search_term: Terme à rechercher
            
        Returns:
            Liste des samples correspondants
        """
        session = self.get_session()
        search = f"%{search_term}%"
        return session.query(MusicSample).filter(
            (MusicSample.title.ilike(search)) | 
            (MusicSample.description.ilike(search)) | 
            (MusicSample.tags.ilike(search)) |
            (MusicSample.genre.ilike(search))
        ).all()
    
    # Méthodes pour la liste de lecture musicale
    def add_playlist_entry(self, url: str, added_by: str, guild_id: str, 
                          title: str = None, duration: int = None) -> PlaylistEntry:
        """
        Ajoute un morceau à la liste de lecture d'un serveur.
        
        Args:
            url: URL de la piste (YouTube ou autre)
            added_by: ID Discord de l'ajouteur
            guild_id: ID du serveur Discord
            title: Titre du morceau
            duration: Durée en secondes
            
        Returns:
            L'objet PlaylistEntry créé
        """
        session = self.get_session()
        entry = PlaylistEntry(
            url=url,
            added_by=added_by,
            guild_id=guild_id,
            title=title,
            duration=duration
        )
        session.add(entry)
        session.commit()
        return entry
    
    def get_playlist(self, guild_id: str, limit: int = 20) -> List[PlaylistEntry]:
        """
        Récupère la liste de lecture d'un serveur.
        
        Args:
            guild_id: ID du serveur Discord
            limit: Nombre maximum d'entrées à récupérer
            
        Returns:
            Liste des entrées de la playlist
        """
        session = self.get_session()
        return session.query(PlaylistEntry)\
            .filter(PlaylistEntry.guild_id == guild_id)\
            .filter(PlaylistEntry.played_at.is_(None))\
            .order_by(PlaylistEntry.added_at)\
            .limit(limit)\
            .all()
    
    def mark_as_played(self, entry_id: int) -> bool:
        """
        Marque une entrée de playlist comme lue.
        
        Args:
            entry_id: ID de l'entrée
            
        Returns:
            True si la mise à jour a réussi, False sinon
        """
        import datetime
        session = self.get_session()
        entry = session.query(PlaylistEntry).filter(PlaylistEntry.id == entry_id).first()
        if entry:
            entry.played_at = datetime.datetime.utcnow()
            session.commit()
            return True
        return False
    
    def clear_playlist(self, guild_id: str) -> int:
        """
        Efface la liste de lecture d'un serveur.
        
        Args:
            guild_id: ID du serveur Discord
            
        Returns:
            Nombre d'entrées supprimées
        """
        session = self.get_session()
        result = session.query(PlaylistEntry)\
            .filter(PlaylistEntry.guild_id == guild_id)\
            .filter(PlaylistEntry.played_at.is_(None))\
            .delete()
        session.commit()
        return result
    
    # Méthodes pour les paramètres de serveur
    def get_guild_settings(self, guild_id: str) -> Optional[GuildSettings]:
        """
        Récupère les paramètres d'un serveur.
        
        Args:
            guild_id: ID du serveur Discord
            
        Returns:
            L'objet GuildSettings ou None si non trouvé
        """
        session = self.get_session()
        settings = session.query(GuildSettings).filter(GuildSettings.guild_id == guild_id).first()
        
        # Créer les paramètres par défaut si non trouvés
        if not settings:
            settings = GuildSettings(guild_id=guild_id)
            session.add(settings)
            session.commit()
        
        return settings
    
    def update_guild_settings(self, guild_id: str, **kwargs) -> GuildSettings:
        """
        Met à jour les paramètres d'un serveur.
        
        Args:
            guild_id: ID du serveur Discord
            **kwargs: Paramètres à mettre à jour
            
        Returns:
            L'objet GuildSettings mis à jour
        """
        session = self.get_session()
        settings = self.get_guild_settings(guild_id)
        
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        session.commit()
        return settings

# Créer une instance globale du gestionnaire de base de données
db_manager = DatabaseManager()