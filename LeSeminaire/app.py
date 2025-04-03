import os
import datetime
import json
from functools import wraps

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///lebot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'warning'

@app.route('/')
def index():
    """Page d'accueil du site"""
    return render_template('index.html', active_page='home')

@app.route('/features')
def features():
    """Page des fonctionnalités du bot"""
    return render_template('features.html', active_page='features')

@app.route('/commands')
def commands():
    """Page des commandes disponibles"""
    return render_template('commands.html', active_page='commands')
    
@app.route('/commands/doc')
def commands_doc():
    """Page de documentation détaillée des commandes"""
    # Récupération de la dernière mise à jour
    last_update = datetime.datetime.now().strftime('%d/%m/%Y')
    
    # Simuler des données pour la documentation (à remplacer par des données réelles)
    command_data = {
        "last_update": last_update
    }
    
    return render_template('commands_doc.html', active_page='commands', **command_data)

@app.route('/resources')
def resources():
    """Page des ressources artistiques"""
    return render_template('resources.html', active_page='resources')

@app.route('/security')
def security():
    """Page des fonctionnalités de sécurité du bot"""
    return render_template('security.html', active_page='security')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Page de contact avec formulaire"""
    from email_validator import validate_email, EmailNotValidError
    import random
    
    success = False
    error = None
    form_data = {}  # Pour conserver les données du formulaire en cas d'erreur
    
    # Créer des questions de sécurité simples pour éviter les bots
    captcha_questions = [
        {"question": "Combien font 2+3 ?", "answer": "5"},
        {"question": "Quelle est la première lettre du mot 'Discord' ?", "answer": "d"},
        {"question": "Combien de jours dans une semaine ?", "answer": "7"},
        {"question": "Quelle est la couleur du ciel par temps clair ?", "answer": "bleu"},
        {"question": "Complétez: Le Sémi...", "answer": "naire"}
    ]
    
    # Sélectionner une question aléatoire (si pas déjà en session)
    if 'captcha_index' not in session:
        session['captcha_index'] = random.randint(0, len(captcha_questions) - 1)
    
    captcha_question = captcha_questions[session['captcha_index']]
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        discord_username = request.form.get('discord_username', '').strip()
        phone = request.form.get('phone', '').strip()
        captcha_answer = request.form.get('captcha_answer', '').strip().lower()
        consent = request.form.get('consent', '')
        
        # Sauvegarder les données du formulaire pour les réafficher en cas d'erreur
        form_data = {
            'name': name,
            'email': email,
            'subject': subject,
            'message': message,
            'discord_username': discord_username,
            'phone': phone
        }
        
        # Validation des champs obligatoires
        if not name or not email or not subject or not message or not consent:
            error = 'Tous les champs marqués * sont obligatoires.'
        elif len(name) < 2:
            error = 'Votre nom doit contenir au moins 2 caractères.'
        elif len(message) < 10:
            error = 'Votre message doit contenir au moins 10 caractères.'
        else:
            # Validation du captcha
            expected_answer = captcha_questions[session['captcha_index']]['answer'].lower()
            if captcha_answer.lower() != expected_answer:
                error = 'La réponse à la question de sécurité est incorrecte.'
            else:
                # Validation avancée de l'email
                try:
                    # Valider et normaliser l'email
                    email_info = validate_email(email, check_deliverability=False)
                    email = email_info.normalized
                    
                    # Définir la priorité du message
                    priority = 0  # Normal par défaut
                    if 'urgent' in subject.lower() or 'important' in subject.lower():
                        priority = 2  # Haute priorité
                    elif discord_username:  # Si l'utilisateur a fourni son nom Discord
                        priority = 1  # Priorité moyenne
                    
                    # Récupérer des informations supplémentaires
                    ip_address = request.remote_addr
                    user_agent = request.user_agent.string if request.user_agent else None
                    
                    # Enregistrer le message de contact
                    contact_message = models.ContactMessage(
                        name=name,
                        email=email,
                        subject=subject,
                        message=message,
                        discord_username=discord_username if discord_username else None,
                        phone=phone if phone else None,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        priority=priority
                    )
                    
                    db.session.add(contact_message)
                    db.session.commit()
                    
                    # Réinitialiser la question captcha pour la prochaine fois
                    session.pop('captcha_index', None)
                    
                    success = True
                    form_data = {}  # Vider les données du formulaire après succès
                except EmailNotValidError as e:
                    error = f"Email invalide : {str(e)}"
    
    return render_template('contact.html', 
                          active_page='contact', 
                          success=success, 
                          error=error, 
                          captcha_question=captcha_question['question'],
                          form_data=form_data)

@app.errorhandler(404)
def page_not_found(e):
    """Gestionnaire d'erreur 404"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Gestionnaire d'erreur 500"""
    return render_template('500.html'), 500

# Importez les modèles et configurez la gestion des admins
import models

@login_manager.user_loader
def load_user(user_id):
    """Charge l'utilisateur à partir de son ID"""
    return db.session.get(models.Admin, int(user_id))


def admin_required(f):
    """Décorateur pour restreindre l'accès aux administrateurs"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Vous devez être connecté en tant qu\'administrateur.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# Routes d'administration
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Page de connexion admin"""
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = db.session.query(models.Admin).filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'danger')
    
    return render_template('admin/login.html')


@app.route('/admin/logout')
@login_required
def admin_logout():
    """Déconnexion admin"""
    logout_user()
    flash('Vous avez été déconnecté.', 'success')
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Tableau de bord admin"""
    # Récupérer les statistiques
    stats = {
        'resources': db.session.query(models.Resource).count(),
        'samples': db.session.query(models.MusicSample).count(),
        'collaborations': db.session.query(models.Collaboration).count(),
        'commands': db.session.query(models.CommandStat).count()
    }
    
    # Récupérer les ressources récentes
    resources = db.session.query(models.Resource).order_by(models.Resource.added_at.desc()).limit(10).all()
    
    # Récupérer les samples récents
    samples = db.session.query(models.MusicSample).order_by(models.MusicSample.added_at.desc()).limit(10).all()
    
    # Récupérer les projets de collaboration
    collaborations = db.session.query(models.Collaboration).order_by(models.Collaboration.updated_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', stats=stats, resources=resources, 
                           samples=samples, collaborations=collaborations)


@app.route('/admin/resources')
@admin_required
def admin_resources():
    """Gestion des ressources artistiques"""
    resources = db.session.query(models.Resource).order_by(models.Resource.added_at.desc()).all()
    return render_template('admin/resources.html', resources=resources)


@app.route('/admin/resource/new', methods=['GET', 'POST'])
@admin_required
def admin_resource_new():
    """Ajout d'une nouvelle ressource"""
    categories = models.ResourceCategory
    
    if request.method == 'POST':
        title = request.form.get('title')
        url = request.form.get('url')
        category_name = request.form.get('category')
        description = request.form.get('description')
        tags = request.form.get('tags')
        added_by = request.form.get('added_by')
        approved = 'approved' in request.form
        
        if not title or not url or not category_name:
            flash('Merci de remplir tous les champs obligatoires.', 'danger')
            return render_template('admin/resource_form.html', categories=categories)
        
        category = getattr(models.ResourceCategory, category_name)
        
        resource = models.Resource(
            title=title,
            url=url,
            category=category,
            description=description,
            tags=tags,
            added_by=added_by,
            approved=approved
        )
        
        db.session.add(resource)
        db.session.commit()
        
        flash('Ressource ajoutée avec succès !', 'success')
        return redirect(url_for('admin_resources'))
    
    return render_template('admin/resource_form.html', categories=categories)


@app.route('/admin/resource/edit/<int:resource_id>', methods=['GET', 'POST'])
@admin_required
def admin_resource_edit(resource_id):
    """Modification d'une ressource"""
    resource = db.session.get(models.Resource, resource_id)
    
    if not resource:
        flash('Ressource non trouvée.', 'danger')
        return redirect(url_for('admin_resources'))
    
    categories = models.ResourceCategory
    
    if request.method == 'POST':
        title = request.form.get('title')
        url = request.form.get('url')
        category_name = request.form.get('category')
        description = request.form.get('description')
        tags = request.form.get('tags')
        added_by = request.form.get('added_by')
        approved = 'approved' in request.form
        
        if not title or not url or not category_name:
            flash('Merci de remplir tous les champs obligatoires.', 'danger')
            return render_template('admin/resource_form.html', resource=resource, categories=categories)
        
        category = getattr(models.ResourceCategory, category_name)
        
        resource.title = title
        resource.url = url
        resource.category = category
        resource.description = description
        resource.tags = tags
        resource.added_by = added_by
        resource.approved = approved
        
        db.session.commit()
        
        flash('Ressource mise à jour avec succès !', 'success')
        return redirect(url_for('admin_resources'))
    
    return render_template('admin/resource_form.html', resource=resource, categories=categories)


@app.route('/admin/resource/delete/<int:resource_id>')
@admin_required
def admin_resource_delete(resource_id):
    """Suppression d'une ressource"""
    resource = db.session.get(models.Resource, resource_id)
    
    if not resource:
        flash('Ressource non trouvée.', 'danger')
        return redirect(url_for('admin_resources'))
    
    db.session.delete(resource)
    db.session.commit()
    
    flash('Ressource supprimée avec succès !', 'success')
    return redirect(url_for('admin_resources'))


@app.route('/admin/samples')
@admin_required
def admin_samples():
    """Gestion des samples musicaux"""
    samples = db.session.query(models.MusicSample).order_by(models.MusicSample.added_at.desc()).all()
    return render_template('admin/samples.html', samples=samples)


@app.route('/admin/sample/new', methods=['GET', 'POST'])
@admin_required
def admin_sample_new():
    """Ajout d'un nouveau sample"""
    if request.method == 'POST':
        title = request.form.get('title')
        url = request.form.get('url')
        description = request.form.get('description')
        bpm = request.form.get('bpm')
        key = request.form.get('key')
        genre = request.form.get('genre')
        tags = request.form.get('tags')
        duration = request.form.get('duration')
        added_by = request.form.get('added_by')
        
        if not title or not url or not added_by:
            flash('Merci de remplir tous les champs obligatoires.', 'danger')
            return render_template('admin/sample_form.html')
        
        sample = models.MusicSample(
            title=title,
            url=url,
            description=description,
            bpm=int(bpm) if bpm else None,
            key=key,
            genre=genre,
            tags=tags,
            duration=int(duration) if duration else None,
            added_by=added_by
        )
        
        db.session.add(sample)
        db.session.commit()
        
        flash('Sample ajouté avec succès !', 'success')
        return redirect(url_for('admin_samples'))
    
    return render_template('admin/sample_form.html')


@app.route('/admin/sample/edit/<int:sample_id>', methods=['GET', 'POST'])
@admin_required
def admin_sample_edit(sample_id):
    """Modification d'un sample"""
    sample = db.session.get(models.MusicSample, sample_id)
    
    if not sample:
        flash('Sample non trouvé.', 'danger')
        return redirect(url_for('admin_samples'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        url = request.form.get('url')
        description = request.form.get('description')
        bpm = request.form.get('bpm')
        key = request.form.get('key')
        genre = request.form.get('genre')
        tags = request.form.get('tags')
        duration = request.form.get('duration')
        added_by = request.form.get('added_by')
        
        if not title or not url or not added_by:
            flash('Merci de remplir tous les champs obligatoires.', 'danger')
            return render_template('admin/sample_form.html', sample=sample)
        
        sample.title = title
        sample.url = url
        sample.description = description
        sample.bpm = int(bpm) if bpm else None
        sample.key = key
        sample.genre = genre
        sample.tags = tags
        sample.duration = int(duration) if duration else None
        sample.added_by = added_by
        
        db.session.commit()
        
        flash('Sample mis à jour avec succès !', 'success')
        return redirect(url_for('admin_samples'))
    
    return render_template('admin/sample_form.html', sample=sample)


@app.route('/admin/sample/delete/<int:sample_id>')
@admin_required
def admin_sample_delete(sample_id):
    """Suppression d'un sample"""
    sample = db.session.get(models.MusicSample, sample_id)
    
    if not sample:
        flash('Sample non trouvé.', 'danger')
        return redirect(url_for('admin_samples'))
    
    db.session.delete(sample)
    db.session.commit()
    
    flash('Sample supprimé avec succès !', 'success')
    return redirect(url_for('admin_samples'))


@app.route('/admin/collaborations')
@admin_required
def admin_collaborations():
    """Gestion des projets de collaboration"""
    collaborations = db.session.query(models.Collaboration).order_by(models.Collaboration.updated_at.desc()).all()
    return render_template('admin/collaborations.html', collaborations=collaborations)


@app.route('/admin/collab/view/<int:collab_id>')
@admin_required
def admin_collab_view(collab_id):
    """Détails d'un projet de collaboration"""
    collab = db.session.get(models.Collaboration, collab_id)
    
    if not collab:
        flash('Projet de collaboration non trouvé.', 'danger')
        return redirect(url_for('admin_collaborations'))
    
    return render_template('admin/collab_view.html', collab=collab)


@app.route('/admin/users')
@admin_required
def admin_users():
    """Gestion des utilisateurs (simulation)"""
    # Dans un environnement réel, nous récupérerions les utilisateurs Discord via l'API
    # Ici, nous simulons quelques utilisateurs pour la démonstration
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    
    # Simulation de données utilisateurs
    users = [
        {
            'id': '123456789012345678',
            'username': 'user1',
            'display_name': 'Utilisateur 1',
            'avatar_url': 'https://cdn.discordapp.com/embed/avatars/0.png',
            'status': 'online',
            'joined_at': datetime.datetime.utcnow() - datetime.timedelta(days=30),
            'created_at': datetime.datetime.utcnow() - datetime.timedelta(days=120),
            'roles': [
                {'name': 'Admin', 'color': '#FF0000'},
                {'name': 'Artiste', 'color': '#00FF00'}
            ],
            'last_activity': 'Aujourd\'hui à 14:30',
            'message_count': 125,
            'command_count': 42,
            'warning_count': 0,
            'notes': None,
            'is_verified': True
        },
        {
            'id': '234567890123456789',
            'username': 'user2',
            'display_name': 'Utilisateur 2',
            'avatar_url': 'https://cdn.discordapp.com/embed/avatars/1.png',
            'status': 'idle',
            'joined_at': datetime.datetime.utcnow() - datetime.timedelta(days=15),
            'created_at': datetime.datetime.utcnow() - datetime.timedelta(days=90),
            'roles': [
                {'name': 'Modérateur', 'color': '#FFFF00'},
                {'name': 'Musicien', 'color': '#0000FF'}
            ],
            'last_activity': 'Hier à 18:45',
            'message_count': 87,
            'command_count': 23,
            'warning_count': 1,
            'notes': 'A reçu un avertissement pour spam le 12/03/2025',
            'is_verified': True
        }
    ]
    
    return render_template('admin/users.html', 
                           users=users,
                           page=page,
                           total_pages=1,
                           total_users=len(users),
                           offset=offset,
                           search_query=request.args.get('search', ''),
                           filters_active=False,
                           active_filters=[])


@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    """Paramètres administrateur"""
    if request.method == 'POST':
        admin_username = request.form.get('admin_username')
        admin_password = request.form.get('admin_password')
        welcome_message = request.form.get('welcome_message')
        
        # Mettre à jour le nom d'utilisateur admin
        if admin_username:
            admin_setting = db.session.query(models.AdminSettings).filter_by(setting_key='admin_username').first()
            if not admin_setting:
                admin_setting = models.AdminSettings(setting_key='admin_username', setting_value=admin_username)
                db.session.add(admin_setting)
            else:
                admin_setting.setting_value = admin_username
        
        # Mettre à jour le mot de passe admin si fourni
        if admin_password:
            current_user.set_password(admin_password)
        
        # Mettre à jour le message de bienvenue
        if welcome_message:
            welcome_setting = db.session.query(models.AdminSettings).filter_by(setting_key='welcome_message').first()
            if not welcome_setting:
                welcome_setting = models.AdminSettings(setting_key='welcome_message', setting_value=welcome_message)
                db.session.add(welcome_setting)
            else:
                welcome_setting.setting_value = welcome_message
        
        db.session.commit()
        flash('Paramètres mis à jour avec succès !', 'success')
        return redirect(url_for('admin_dashboard'))
    
    # Récupérer les paramètres actuels
    settings = {}
    
    admin_username = db.session.query(models.AdminSettings).filter_by(setting_key='admin_username').first()
    if admin_username:
        settings['admin_username'] = admin_username.setting_value
    else:
        settings['admin_username'] = current_user.username
    
    welcome_message = db.session.query(models.AdminSettings).filter_by(setting_key='welcome_message').first()
    if welcome_message:
        settings['welcome_message'] = welcome_message.setting_value
    else:
        settings['welcome_message'] = "Bienvenue sur le serveur ! N'oubliez pas de lire les règles et de vous présenter."
    
    return render_template('admin/settings.html', settings=settings)


@app.route('/admin/send-dm/<user_id>', methods=['POST'])
@admin_required
def admin_send_dm(user_id):
    """Envoyer un message direct via le bot (simulation)"""
    data = request.get_json()
    message = data.get('message', '')
    
    if not message:
        return jsonify({'success': False, 'error': 'Message vide'})
    
    # Dans un environnement réel, nous enverrions le message via l'API Discord
    # Ici, nous simulons juste une réponse positive
    
    return jsonify({'success': True})


@app.route('/stats')
@app.route('/statistiques')
def show_stats():
    """Page de statistiques du bot"""
    # Simuler des données pour les graphiques
    days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    command_data = [42, 37, 53, 62, 51, 33, 45]
    music_data = [15, 22, 18, 27, 19, 34, 29]
    
    category_labels = ['Général', 'Modération', 'Musique', 'Ressources', 'Rôles', 'Admin']
    category_data = [25, 18, 32, 15, 7, 3]
    
    resource_labels = list(cat.value for cat in models.ResourceCategory)
    resource_data = [5, 12, 8, 6, 4, 7, 3, 9, 2, 1]
    
    # Statistiques globales
    stats = {
        'servers': 10,
        'total_users': 347,
        'uptime': '7j 3h 12m',
        'ping': 42,
        'command_count': 1253,
        'commands_today': 132,
        'songs_played': 853,
        'music_hours': 24
    }
    
    # Top commandes
    top_commands = [
        {'name': 'play', 'category': 'music', 'uses': 324, 'percentage': 100},
        {'name': 'help', 'category': 'general', 'uses': 253, 'percentage': 78},
        {'name': 'ping', 'category': 'general', 'uses': 187, 'percentage': 58},
        {'name': 'skip', 'category': 'music', 'uses': 152, 'percentage': 47},
        {'name': 'art_resources', 'category': 'resources', 'uses': 118, 'percentage': 36},
        {'name': 'queue', 'category': 'music', 'uses': 95, 'percentage': 29},
        {'name': 'pause', 'category': 'music', 'uses': 82, 'percentage': 25},
        {'name': 'resume', 'category': 'music', 'uses': 77, 'percentage': 24},
        {'name': 'stop', 'category': 'music', 'uses': 63, 'percentage': 19},
        {'name': 'clear', 'category': 'moderation', 'uses': 54, 'percentage': 17}
    ]
    
    # Top ressources
    top_resources = [
        {'title': 'Guide de l\'intermittence', 'description': 'Tout savoir sur le statut d\'intermittent du spectacle', 'category': 'Business', 'added_by': 'Admin', 'views': 124},
        {'title': 'Tutoriel Mixage Audio', 'description': 'Guide complet pour le mixage audio professionnel', 'category': 'Mixage', 'added_by': 'User1', 'views': 98},
        {'title': 'Masterisation en home studio', 'description': 'Techniques de masterisation à petit budget', 'category': 'Mastering', 'added_by': 'User2', 'views': 87},
        {'title': 'Formation Ableton Live', 'description': 'Cours complet sur Ableton Live 11', 'category': 'Production', 'added_by': 'User3', 'views': 76},
        {'title': 'Droits d\'auteur SACEM', 'description': 'Comment protéger vos œuvres musicales', 'category': 'Juridique', 'added_by': 'Admin', 'views': 65}
    ]
    
    # Top chansons
    top_songs = [
        {'title': 'Titre chanson 1', 'duration': '3:45', 'added_by': 'User1', 'plays': 28},
        {'title': 'Titre chanson 2', 'duration': '4:12', 'added_by': 'User2', 'plays': 22},
        {'title': 'Titre chanson 3', 'duration': '3:21', 'added_by': 'User3', 'plays': 18},
        {'title': 'Titre chanson 4', 'duration': '5:07', 'added_by': 'User1', 'plays': 15},
        {'title': 'Titre chanson 5', 'duration': '2:59', 'added_by': 'User4', 'plays': 12}
    ]
    
    return render_template('stats.html', active_page='stats',
                          days=json.dumps(days), command_data=json.dumps(command_data),
                          music_data=json.dumps(music_data), 
                          category_labels=json.dumps(category_labels),
                          category_data=json.dumps(category_data),
                          resource_labels=json.dumps(resource_labels),
                          resource_data=json.dumps(resource_data),
                          stats=stats, top_commands=top_commands,
                          top_resources=top_resources, top_songs=top_songs,
                          last_update=datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'))


@app.route('/stats/realtime')
@app.route('/realtime-stats')
def realtime_stats():
    """Page de statistiques en temps réel du bot"""
    # Récupérer les données réelles à partir de la base de données
    last_update = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    from models import ServerStat, ChannelStat, UserStat, EngagementData, CommandStat
    from sqlalchemy import func, desc
    import json
    import os
    import time
    import psutil
    import random  # Pour compléter certaines données non disponibles actuellement
    
    uptime = {
        'days': 0,
        'hours': 0,
        'minutes': 0
    }
    
    try:
        # Calculer l'uptime réel si possible
        proc = psutil.Process()
        uptime_seconds = time.time() - proc.create_time()
        uptime['days'] = int(uptime_seconds // (60 * 60 * 24))
        uptime['hours'] = int((uptime_seconds % (60 * 60 * 24)) // (60 * 60))
        uptime['minutes'] = int((uptime_seconds % (60 * 60)) // 60)
    except Exception as e:
        app.logger.warning(f"Erreur lors du calcul de l'uptime: {e}")
        # Valeurs par défaut
        uptime = {'days': 7, 'hours': 3, 'minutes': 12}
    
    try:
        # Utilisation CPU/RAM actuelle
        cpu_usage = psutil.cpu_percent(interval=0.1)
        ram_usage = psutil.Process().memory_info().rss // (1024 * 1024)  # en MB
    except Exception as e:
        app.logger.warning(f"Erreur lors de la récupération des données système: {e}")
        cpu_usage = 24
        ram_usage = 256
    
    # Version du bot
    version = os.environ.get('BOT_VERSION', '1.2.0')
    
    try:
        # Statistiques générales tirées de la base de données
        total_users = db.session.query(func.count(func.distinct(UserStat.user_id))).scalar() or 0
        total_servers = db.session.query(func.count(func.distinct(ServerStat.guild_id))).scalar() or 0
        
        # Commandes utilisées aujourd'hui
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        commands_today = db.session.query(func.count('*')).select_from(CommandStat).filter(
            CommandStat.used_at >= today
        ).scalar() or 0
        
        # Total des musiques jouées
        from models import PlaylistEntry
        total_songs = db.session.query(func.count('*')).select_from(PlaylistEntry).filter(
            PlaylistEntry.played_at.isnot(None)
        ).scalar() or 0
        
        # Données d'engagement sur 30 jours
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        engagement_data = db.session.query(EngagementData).filter(
            EngagementData.timestamp >= thirty_days_ago
        ).order_by(EngagementData.timestamp.asc()).all()
        
        # Construire les données pour le graphique de croissance des utilisateurs
        user_growth_dates = []
        user_growth_counts = []
        last_count = 0
        
        if engagement_data:
            for data in engagement_data:
                date_str = data.timestamp.strftime("%d/%m")
                if date_str not in user_growth_dates:
                    user_growth_dates.append(date_str)
                    user_growth_counts.append(data.total_members)
                    last_count = data.total_members
        
        # Si on a moins de 30 points, compléter avec les dernières valeurs connues
        while len(user_growth_dates) < 30:
            next_day = (datetime.datetime.strptime(user_growth_dates[-1], "%d/%m") if user_growth_dates 
                      else thirty_days_ago).date() + datetime.timedelta(days=1)
            user_growth_dates.append(next_day.strftime("%d/%m"))
            last_count += random.randint(0, 2)  # Légère croissance aléatoire
            user_growth_counts.append(last_count)
        
        user_growth_labels = json.dumps(user_growth_dates)
        user_growth_data = json.dumps(user_growth_counts)
        
        # Données pour les commandes par catégorie
        command_categories = db.session.query(
            CommandStat.category, func.count('*')
        ).group_by(CommandStat.category).all()
        
        category_names = []
        category_counts = []
        
        for category, count in command_categories:
            if category:
                category_names.append(category)
                category_counts.append(count)
        
        # Ajouter les catégories standard si manquantes
        standard_categories = ["Général", "Modération", "Musique", "Ressources", "Rôles", "Admin"]
        for cat in standard_categories:
            if cat not in category_names:
                category_names.append(cat)
                category_counts.append(0)
        
        command_category_labels = json.dumps(category_names)
        command_category_data = json.dumps(category_counts)
        
        # Données pour l'activité par heure
        # Une approche simplifiée pour éviter les problèmes avec astext
        hourly_data = []
        try:
            hours_stats = db.session.query(
                func.extract('hour', ServerStat.timestamp).label('hour'),
                ServerStat.data
            ).filter(
                ServerStat.type == 'hourly'
            ).order_by('hour').all()
            
            # Grouper par heure manuellement
            hour_groups = {}
            for hour, data_str in hours_stats:
                if hour is not None:
                    hour_int = int(hour)
                    if hour_int not in hour_groups:
                        hour_groups[hour_int] = []
                    
                    if data_str:
                        try:
                            data = json.loads(data_str) if isinstance(data_str, str) else data_str
                            if isinstance(data, dict) and 'message_count' in data:
                                hour_groups[hour_int].append(data['message_count'])
                        except (json.JSONDecodeError, TypeError):
                            pass
            
            # Calculer la moyenne pour chaque heure
            for hour, counts in hour_groups.items():
                if counts:
                    avg = sum(counts) / len(counts)
                    hourly_data.append((hour, avg))
        except Exception as e:
            app.logger.error(f"Erreur lors de l'analyse des données horaires: {e}")
        
        hourly_activity = [0] * 24  # Initialiser pour les 24 heures
        
        for hour, avg_messages in hourly_data:
            if hour is not None and 0 <= int(hour) < 24:
                hourly_activity[int(hour)] = int(avg_messages) if avg_messages else 0
        
        hourly_activity_labels = json.dumps([f"{i}h" for i in range(24)])
        hourly_activity_data = json.dumps(hourly_activity)
        
        # Serveurs connectés
        servers = []
        server_ids = db.session.query(func.distinct(ServerStat.guild_id)).filter(
            ServerStat.guild_id.isnot(None)
        ).limit(5).all()
        
        for server_id in server_ids:
            if server_id[0]:  # Extraire l'ID de serveur du tuple
                # Récupérer le dernier relevé pour ce serveur
                latest_stat = db.session.query(ServerStat).filter(
                    ServerStat.guild_id == server_id[0]
                ).order_by(ServerStat.timestamp.desc()).first()
                
                if latest_stat and latest_stat.data:
                    data = json.loads(latest_stat.data) if isinstance(latest_stat.data, str) else latest_stat.data
                    member_count = data.get('active_users', 0)
                    
                    servers.append({
                        'name': f"Serveur {server_id[0][-4:]}",  # Utiliser les 4 derniers chiffres de l'ID
                        'icon': None,
                        'member_count': member_count,
                        'premium': member_count > 50  # Exemple de critère pour "premium"
                    })
        
        # Compléter avec des données par défaut si nécessaire
        if not servers:
            servers = [
                {'name': 'Le Séminaire', 'icon': None, 'member_count': 125, 'premium': True},
                {'name': 'MusicMakers', 'icon': None, 'member_count': 87, 'premium': True}
            ]
        
        # Activités récentes
        activities = []
        recent_commands = db.session.query(CommandStat).order_by(
            CommandStat.used_at.desc()
        ).limit(5).all()
        
        for cmd in recent_commands:
            time_str = cmd.used_at.strftime('%H:%M')
            content = f"Utilisateur \"{cmd.user_id[-4:]}\" a utilisé la commande !{cmd.command_name}"
            activities.append({'type': 'Command', 'content': content, 'time': time_str})
        
        # Compléter avec des données par défaut si nécessaire
        if len(activities) < 5:
            default_activities = [
                {'type': 'Command', 'content': 'Utilisateur "MusicMaker123" a utilisé la commande !play', 'time': '11:42'},
                {'type': 'Server Join', 'content': 'Le bot a rejoint le serveur "Creative Minds"', 'time': '11:35'},
                {'type': 'Error', 'content': 'Erreur lors de l\'exécution de la commande !skip - Aucune musique en cours', 'time': '11:28'},
                {'type': 'Command', 'content': 'Utilisateur "Admin51" a utilisé la commande !ban', 'time': '11:20'},
                {'type': 'Command', 'content': 'Utilisateur "DJ_Master" a utilisé la commande !queue', 'time': '11:15'}
            ]
            activities.extend(default_activities[:5-len(activities)])
        
        # Métriques avancées - Calculer à partir des données réelles si possible
        if engagement_data and len(engagement_data) > 0:
            latest_engagement = engagement_data[-1]
            if latest_engagement.total_members > 0:
                engagement_rate = (latest_engagement.active_members / latest_engagement.total_members) * 100
            else:
                engagement_rate = 0
            
            # Simuler d'autres métriques avancées basées sur des données réelles
            response_rate = 95 + (engagement_rate / 20)  # Plus l'engagement est élevé, meilleur est le taux de réponse
            avg_commands_per_server = commands_today / max(1, total_servers)
            avg_response_time = 150 - (engagement_rate / 2)  # Plus l'engagement est élevé, plus la réponse est rapide
        else:
            # Valeurs par défaut
            engagement_rate = 64.7
            response_rate = 98.2
            avg_commands_per_server = 152
            avg_response_time = 124
        
        # Arrondir les valeurs
        engagement_rate = round(engagement_rate, 1)
        response_rate = round(response_rate, 1)
        avg_commands_per_server = round(avg_commands_per_server, 1)
        avg_response_time = round(avg_response_time, 1)
        
        # Données pour les nouveaux utilisateurs par jour
        user_join_data = []
        
        # Récupérer les données de jointure des 30 derniers jours
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        join_dates = []
        join_counts = []
        
        # Agréger par date
        last_30_days = [(datetime.datetime.now() - datetime.timedelta(days=i)).strftime('%d/%m') for i in range(30)]
        last_30_days.reverse()  # Ordre chronologique
        
        # Compter les nouveaux membres par jour (simulé pour le moment)
        new_users_counts = []
        for _ in range(len(last_30_days)):
            new_users_counts.append(random.randint(1, 20))
        
        new_users_labels = json.dumps(last_30_days)
        new_users_data = json.dumps(new_users_counts)
        
        # Données pour le taux de rétention hebdomadaire
        retention_labels = ['Semaine 1', 'Semaine 2', 'Semaine 3', 'Semaine 4']
        
        # Simuler des taux de rétention décroissants
        initial_rate = min(100, 50 + engagement_rate)
        retention_data = [
            initial_rate,
            initial_rate * 0.8,
            initial_rate * 0.7,
            initial_rate * 0.65
        ]
        retention_data = [round(rate, 1) for rate in retention_data]
        
        # Localisation des serveurs (simulée)
        map_locations = [
            {'lat': 48.8566, 'lng': 2.3522, 'count': 5, 'location': 'Paris, France'},
            {'lat': 51.5074, 'lng': -0.1278, 'count': 4, 'location': 'Londres, UK'},
            {'lat': 40.7128, 'lng': -74.0060, 'count': 7, 'location': 'New York, USA'},
            {'lat': 55.7558, 'lng': 37.6173, 'count': 3, 'location': 'Moscou, Russie'},
            {'lat': 35.6895, 'lng': 139.6917, 'count': 4, 'location': 'Tokyo, Japon'}
        ]
        
        map_data = json.dumps(map_locations)
        
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération des données de statistiques: {e}")
        # Utiliser des valeurs par défaut en cas d'erreur
        total_users = 347
        total_servers = 10
        commands_today = 132
        total_songs = 853
        
        user_growth_labels = json.dumps([f"{i}" for i in range(1, 31)])
        user_growth_data = json.dumps([300 + i for i in range(30)])
        
        command_category_labels = json.dumps(["Général", "Modération", "Musique", "Ressources", "Rôles", "Admin"])
        command_category_data = json.dumps([25, 18, 32, 15, 7, 3])
        
        hourly_activity_labels = json.dumps([f"{i}h" for i in range(24)])
        hourly_activity_data = json.dumps([random.randint(1, 30) for _ in range(24)])
        
        servers = [
            {'name': 'Le Séminaire', 'icon': None, 'member_count': 125, 'premium': True},
            {'name': 'MusicMakers', 'icon': None, 'member_count': 87, 'premium': True}
        ]
        
        activities = [
            {'type': 'Command', 'content': 'Utilisateur "MusicMaker123" a utilisé la commande !play', 'time': '11:42'},
            {'type': 'Server Join', 'content': 'Le bot a rejoint le serveur "Creative Minds"', 'time': '11:35'},
            {'type': 'Error', 'content': 'Erreur lors de l\'exécution de la commande !skip - Aucune musique en cours', 'time': '11:28'},
            {'type': 'Command', 'content': 'Utilisateur "Admin51" a utilisé la commande !ban', 'time': '11:20'},
            {'type': 'Command', 'content': 'Utilisateur "DJ_Master" a utilisé la commande !queue', 'time': '11:15'}
        ]
        
        engagement_rate = 64.7
        response_rate = 98.2
        avg_commands_per_server = 152
        avg_response_time = 124
        
        new_users_labels = json.dumps(['01/04', '05/04', '10/04', '15/04', '20/04', '25/04', '30/04'])
        new_users_data = json.dumps([5, 8, 12, 7, 9, 15, 10])
        
        retention_labels = json.dumps(['Semaine 1', 'Semaine 2', 'Semaine 3', 'Semaine 4'])
        retention_data = json.dumps([100, 75, 65, 60])
        
        map_data = json.dumps([
            {'lat': 48.8566, 'lng': 2.3522, 'count': 5, 'location': 'Paris, France'},
            {'lat': 51.5074, 'lng': -0.1278, 'count': 4, 'location': 'Londres, UK'},
            {'lat': 40.7128, 'lng': -74.0060, 'count': 7, 'location': 'New York, USA'}
        ])
    
    return render_template('realtime_stats.html',
                          active_page='stats',
                          last_update=last_update,
                          uptime=uptime,
                          ping=avg_response_time,  # Utiliser le temps de réponse moyen comme ping
                          cpu_usage=cpu_usage,
                          ram_usage=ram_usage,
                          version=version,
                          total_users=total_users,
                          total_servers=total_servers,
                          commands_today=commands_today,
                          total_songs=total_songs,
                          user_growth_labels=user_growth_labels,
                          user_growth_data=user_growth_data,
                          command_category_labels=command_category_labels,
                          command_category_data=command_category_data,
                          hourly_activity_labels=hourly_activity_labels,
                          hourly_activity_data=hourly_activity_data,
                          servers=servers,
                          activities=activities,
                          engagement_rate=engagement_rate,
                          response_rate=response_rate,
                          avg_commands_per_server=avg_commands_per_server,
                          avg_response_time=avg_response_time,
                          map_data=map_data,
                          new_users_labels=new_users_labels,
                          new_users_data=new_users_data,
                          retention_labels=json.dumps(retention_labels),
                          retention_data=json.dumps(retention_data))


# Initialisation de la base de données et création d'un admin par défaut si nécessaire
def initialize_db():
    """Initialise la base de données et crée un admin par défaut si nécessaire"""
    # Créer les tables
    db.create_all()
    
    # Vérifier s'il existe déjà un administrateur
    admin_exists = db.session.query(models.Admin).first() is not None
    
    if not admin_exists:
        # Créer un admin par défaut
        admin = models.Admin(
            username='admin',
            email='admin@leseminaire.org'
        )
        admin.set_password('admin123')  # À changer après la première connexion !
        
        db.session.add(admin)
        db.session.commit()

# Exécuter l'initialisation de la base de données lors du chargement de l'application
with app.app_context():
    import models
    initialize_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)