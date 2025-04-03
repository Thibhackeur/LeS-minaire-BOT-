"""
Module de gestion des collaborations artistiques pour LeSéminaire[BOT].
Permet aux artistes de créer et gérer des projets de collaboration.
"""
import discord
from discord.ext import commands
import asyncio
import logging
from typing import Optional, List, Dict
from database import db_manager
from models import Collaboration, CollaborationMember

logger = logging.getLogger(__name__)

class CollaborationView(discord.ui.View):
    """Vue pour afficher les collaborations avec pagination"""
    
    def __init__(self, collaborations, author_id, timeout=180):
        super().__init__(timeout=timeout)
        self.collaborations = collaborations
        self.author_id = author_id
        self.current_page = 0
        self.items_per_page = 5
    
    @property
    def max_pages(self):
        """Calcule le nombre total de pages"""
        return max(1, (len(self.collaborations) + self.items_per_page - 1) // self.items_per_page)
    
    def get_current_page_embed(self):
        """Génère l'embed pour la page actuelle"""
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.collaborations))
        
        embed = discord.Embed(
            title="🤝 Projets de Collaboration",
            description="Voici les projets de collaboration en cours :",
            color=0xf1c40f
        )
        
        if not self.collaborations:
            embed.add_field(name="Aucun projet trouvé", value="Utilisez `!collab create` pour créer un nouveau projet.")
            return embed
        
        for collab in self.collaborations[start_idx:end_idx]:
            status_emoji = "🟢" if collab.status == "En cours" else "🔴" if collab.status == "Terminé" else "⚪"
            
            value = f"{collab.description or 'Aucune description'}\n"
            value += f"**Status:** {status_emoji} {collab.status}\n"
            value += f"**Créé le:** {collab.created_at.strftime('%d/%m/%Y')}\n"
            value += f"**ID:** {collab.id}"
            
            embed.add_field(
                name=f"{collab.title}",
                value=value,
                inline=False
            )
        
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages} • Total: {len(self.collaborations)} projets")
        return embed
    
    @discord.ui.button(label="◀️ Précédent", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Passe à la page précédente"""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Vous ne pouvez pas contrôler ce menu.", ephemeral=True)
            return
        
        self.current_page = max(0, self.current_page - 1)
        await interaction.response.edit_message(embed=self.get_current_page_embed())
    
    @discord.ui.button(label="▶️ Suivant", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Passe à la page suivante"""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Vous ne pouvez pas contrôler ce menu.", ephemeral=True)
            return
        
        self.current_page = min(self.max_pages - 1, self.current_page + 1)
        await interaction.response.edit_message(embed=self.get_current_page_embed())

class JoinCollaborationView(discord.ui.View):
    """Vue pour rejoindre un projet de collaboration"""
    
    def __init__(self, collab_id, creator_id, timeout=86400):  # 24 heures
        super().__init__(timeout=timeout)
        self.collab_id = collab_id
        self.creator_id = creator_id
        self.members = []
    
    @discord.ui.button(label="Rejoindre le projet", style=discord.ButtonStyle.success, emoji="🤝")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bouton pour rejoindre un projet"""
        # Vérifier si l'utilisateur a déjà rejoint
        if interaction.user.id in [member.id for member in self.members]:
            await interaction.response.send_message("Vous avez déjà rejoint ce projet.", ephemeral=True)
            return
        
        # Ajouter l'utilisateur à la liste des membres
        self.members.append(interaction.user)
        
        # Ajouter à la base de données
        session = db_manager.get_session()
        member = CollaborationMember(
            collaboration_id=self.collab_id,
            member_id=str(interaction.user.id)
        )
        session.add(member)
        session.commit()
        
        # Informer le créateur et l'utilisateur
        creator = interaction.client.get_user(self.creator_id)
        if creator:
            try:
                await creator.send(f"🤝 **{interaction.user.display_name}** a rejoint votre projet de collaboration!")
            except discord.Forbidden:
                pass
        
        await interaction.response.send_message(f"✅ Vous avez rejoint le projet avec succès! Le créateur ({creator.mention if creator else 'le créateur'}) a été informé.", ephemeral=True)

class CollaborationCog(commands.Cog):
    """Cog pour la gestion des collaborations artistiques"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_collab_views = {}  # {collab_id: view}
    
    @commands.group(name="collab", aliases=["collaboration", "projet", "project"])
    async def collab(self, ctx):
        """Commandes de gestion des projets de collaboration artistique"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🤝 Commandes de Collaboration",
                description="Voici les commandes disponibles pour gérer les projets de collaboration :",
                color=0xf1c40f
            )
            
            embed.add_field(
                name="!collab create <titre> [description]",
                value="Crée un nouveau projet de collaboration",
                inline=False
            )
            
            embed.add_field(
                name="!collab list [status]",
                value="Liste les projets de collaboration (status: en_cours, terminé, tous)",
                inline=False
            )
            
            embed.add_field(
                name="!collab info <id>",
                value="Affiche les détails d'un projet spécifique",
                inline=False
            )
            
            embed.add_field(
                name="!collab join <id>",
                value="Rejoindre un projet de collaboration",
                inline=False
            )
            
            embed.add_field(
                name="!collab update <id> status <status>",
                value="Met à jour le statut d'un projet (status: en_cours, terminé, abandonné)",
                inline=False
            )
            
            embed.add_field(
                name="!collab invite <id>",
                value="Invite des membres à rejoindre un projet",
                inline=False
            )
            
            embed.set_footer(text="Le Séminaire - Système de collaborations artistiques")
            await ctx.send(embed=embed)
    
    @collab.command(name="create")
    async def create_collab(self, ctx, title: str, *, description: Optional[str] = None):
        """
        Crée un nouveau projet de collaboration.
        
        Exemple: !collab create "Projet Beat Tape" Création d'une beat tape collective pour la communauté
        """
        session = db_manager.get_session()
        
        # Créer le projet dans la base de données
        collaboration = Collaboration(
            title=title,
            description=description,
            created_by=str(ctx.author.id)
        )
        session.add(collaboration)
        session.flush()  # Pour obtenir l'ID généré
        
        # Ajouter le créateur comme premier membre
        member = CollaborationMember(
            collaboration_id=collaboration.id,
            member_id=str(ctx.author.id),
            role="Créateur"
        )
        session.add(member)
        session.commit()
        
        # Créer l'embed de confirmation
        embed = discord.Embed(
            title="✅ Projet créé",
            description=f"Votre projet de collaboration **{title}** a été créé avec succès!",
            color=0x2ecc71
        )
        
        embed.add_field(name="ID du projet", value=collaboration.id, inline=True)
        embed.add_field(name="Statut", value="En cours", inline=True)
        
        if description:
            embed.add_field(name="Description", value=description, inline=False)
        
        embed.add_field(
            name="Prochaines étapes",
            value="Utilisez `!collab invite " + str(collaboration.id) + "` pour inviter des membres à rejoindre votre projet.",
            inline=False
        )
        
        embed.set_footer(text=f"Créé par {ctx.author.display_name} | {ctx.guild.name}")
        
        await ctx.send(embed=embed)
    
    @collab.command(name="list")
    async def list_collabs(self, ctx, status: Optional[str] = None):
        """
        Liste les projets de collaboration.
        
        Exemple: !collab list en_cours
        """
        session = db_manager.get_session()
        query = session.query(Collaboration)
        
        if status:
            status_map = {
                "en_cours": "En cours",
                "termine": "Terminé",
                "terminé": "Terminé",
                "abandonne": "Abandonné",
                "abandonné": "Abandonné"
            }
            
            if status.lower() in status_map:
                query = query.filter(Collaboration.status == status_map[status.lower()])
        
        collaborations = query.all()
        
        if not collaborations:
            status_text = f" avec le statut '{status}'" if status else ""
            await ctx.send(f"Aucun projet de collaboration{status_text} trouvé.")
            return
        
        view = CollaborationView(collaborations, ctx.author.id)
        await ctx.send(embed=view.get_current_page_embed(), view=view)
    
    @collab.command(name="info")
    async def collab_info(self, ctx, collab_id: int):
        """
        Affiche les détails d'un projet spécifique.
        
        Exemple: !collab info 42
        """
        session = db_manager.get_session()
        collab = session.query(Collaboration).filter(Collaboration.id == collab_id).first()
        
        if not collab:
            await ctx.send(f"❌ Projet avec ID {collab_id} non trouvé.")
            return
        
        # Récupérer les membres du projet
        members_db = session.query(CollaborationMember).filter(CollaborationMember.collaboration_id == collab_id).all()
        
        embed = discord.Embed(
            title=f"🤝 Projet: {collab.title}",
            description=collab.description or "Aucune description",
            color=0xf1c40f
        )
        
        status_emoji = "🟢" if collab.status == "En cours" else "🔴" if collab.status == "Terminé" else "⚪"
        embed.add_field(name="Statut", value=f"{status_emoji} {collab.status}", inline=True)
        embed.add_field(name="ID", value=collab.id, inline=True)
        
        # Information sur le créateur
        creator_id = collab.created_by
        try:
            creator = await self.bot.fetch_user(int(creator_id))
            creator_name = creator.display_name
            creator_mention = creator.mention
        except (ValueError, discord.errors.NotFound):
            creator_name = "Utilisateur inconnu"
            creator_mention = creator_id
        
        embed.add_field(name="Créé par", value=creator_mention, inline=True)
        embed.add_field(name="Créé le", value=collab.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="Dernière mise à jour", value=collab.updated_at.strftime("%d/%m/%Y"), inline=True)
        
        # Liste des membres
        members_text = ""
        for i, member_db in enumerate(members_db, start=1):
            try:
                member = await self.bot.fetch_user(int(member_db.member_id))
                member_name = member.mention
            except (ValueError, discord.errors.NotFound):
                member_name = f"Utilisateur {member_db.member_id}"
            
            role_text = f" ({member_db.role})" if member_db.role else ""
            members_text += f"{i}. {member_name}{role_text}\n"
        
        if members_text:
            embed.add_field(name=f"Membres ({len(members_db)})", value=members_text, inline=False)
        else:
            embed.add_field(name="Membres", value="Aucun membre dans ce projet", inline=False)
        
        embed.set_footer(text="Le Séminaire - Système de collaborations artistiques")
        await ctx.send(embed=embed)
    
    @collab.command(name="join")
    async def join_collab(self, ctx, collab_id: int):
        """
        Rejoindre un projet de collaboration.
        
        Exemple: !collab join 42
        """
        session = db_manager.get_session()
        collab = session.query(Collaboration).filter(Collaboration.id == collab_id).first()
        
        if not collab:
            await ctx.send(f"❌ Projet avec ID {collab_id} non trouvé.")
            return
        
        # Vérifier si l'utilisateur est déjà membre
        existing_member = session.query(CollaborationMember).filter(
            CollaborationMember.collaboration_id == collab_id,
            CollaborationMember.member_id == str(ctx.author.id)
        ).first()
        
        if existing_member:
            await ctx.send("❌ Vous êtes déjà membre de ce projet.")
            return
        
        # Ajouter l'utilisateur comme membre
        member = CollaborationMember(
            collaboration_id=collab_id,
            member_id=str(ctx.author.id)
        )
        session.add(member)
        session.commit()
        
        # Notifier le créateur
        try:
            creator = await self.bot.fetch_user(int(collab.created_by))
            await creator.send(f"🤝 **{ctx.author.display_name}** a rejoint votre projet de collaboration '{collab.title}'!")
        except (ValueError, discord.errors.NotFound, discord.Forbidden):
            pass
        
        await ctx.send(f"✅ Vous avez rejoint le projet **{collab.title}** avec succès!")
    
    @collab.command(name="update")
    async def update_collab(self, ctx, collab_id: int, field: str, *, value: str):
        """
        Met à jour un projet de collaboration.
        
        Exemple: !collab update 42 status terminé
        """
        session = db_manager.get_session()
        collab = session.query(Collaboration).filter(Collaboration.id == collab_id).first()
        
        if not collab:
            await ctx.send(f"❌ Projet avec ID {collab_id} non trouvé.")
            return
        
        # Vérifier les droits (seul le créateur peut modifier)
        if collab.created_by != str(ctx.author.id):
            await ctx.send("❌ Seul le créateur du projet peut le modifier.")
            return
        
        field = field.lower()
        
        if field == "status" or field == "statut":
            status_map = {
                "en_cours": "En cours",
                "encours": "En cours",
                "termine": "Terminé",
                "terminé": "Terminé",
                "fini": "Terminé",
                "abandonne": "Abandonné",
                "abandonné": "Abandonné"
            }
            
            if value.lower() in status_map:
                collab.status = status_map[value.lower()]
                session.commit()
                await ctx.send(f"✅ Le statut du projet a été mis à jour: **{collab.status}**")
            else:
                await ctx.send("❌ Statut non reconnu. Utilisez: en_cours, terminé, ou abandonné.")
        
        elif field == "description":
            collab.description = value
            session.commit()
            await ctx.send(f"✅ La description du projet a été mise à jour.")
        
        elif field == "title" or field == "titre":
            collab.title = value
            session.commit()
            await ctx.send(f"✅ Le titre du projet a été mis à jour: **{value}**")
        
        else:
            await ctx.send("❌ Champ non reconnu. Champs disponibles: status, description, title")
    
    @collab.command(name="invite")
    async def invite_to_collab(self, ctx, collab_id: int, *, members: Optional[str] = None):
        """
        Invite des membres à rejoindre un projet.
        
        Exemple: !collab invite 42 @user1 @user2
        """
        session = db_manager.get_session()
        collab = session.query(Collaboration).filter(Collaboration.id == collab_id).first()
        
        if not collab:
            await ctx.send(f"❌ Projet avec ID {collab_id} non trouvé.")
            return
        
        # Vérifier les droits (seul le créateur peut inviter)
        if collab.created_by != str(ctx.author.id):
            await ctx.send("❌ Seul le créateur du projet peut inviter des membres.")
            return
        
        # Créer l'embed d'invitation
        embed = discord.Embed(
            title=f"🤝 Invitation à rejoindre '{collab.title}'",
            description=collab.description or "Aucune description",
            color=0xf1c40f
        )
        
        embed.add_field(name="Créateur", value=ctx.author.mention, inline=True)
        embed.add_field(name="Statut", value=collab.status, inline=True)
        
        embed.add_field(
            name="Comment rejoindre",
            value="Cliquez sur le bouton ci-dessous ou utilisez la commande:\n"
                 f"`!collab join {collab_id}`",
            inline=False
        )
        
        embed.set_footer(text=f"ID du projet: {collab_id} | Le Séminaire")
        
        # Créer la vue avec le bouton de participation
        view = JoinCollaborationView(collab_id, ctx.author.id)
        self.active_collab_views[collab_id] = view
        
        if members:
            # Mentionner les utilisateurs spécifiques
            mentions = ctx.message.mentions
            if mentions:
                message = await ctx.send(
                    ", ".join(user.mention for user in mentions) + " vous êtes invités à rejoindre ce projet:",
                    embed=embed,
                    view=view
                )
            else:
                message = await ctx.send(embed=embed, view=view)
        else:
            # Invitation générale
            message = await ctx.send(embed=embed, view=view)
        
        # Stocker l'ID du message pour pouvoir le référencer plus tard
        view.message = message

# Fonction d'installation du cog
async def setup(bot):
    await bot.add_cog(CollaborationCog(bot))