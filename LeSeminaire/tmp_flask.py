import os

from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


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

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html data-bs-theme="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LeSéminaire[BOT] - Dashboard</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <div class="row">
                <div class="col-md-8 offset-md-2">
                    <div class="card shadow">
                        <div class="card-header bg-dark text-white">
                            <h2 class="mb-0">LeSéminaire[BOT] - Interface d'Administration</h2>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-success">
                                <strong>Statut du Bot:</strong> En ligne et opérationnel
                            </div>
                            
                            <h4 class="mt-4">Fonctionnalités Principales</h4>
                            <ul class="list-group mb-4">
                                <li class="list-group-item">✅ Messages de bienvenue personnalisés</li>
                                <li class="list-group-item">✅ Système de vérification en deux étapes</li>
                                <li class="list-group-item">✅ Attribution automatique de rôles</li>
                                <li class="list-group-item">✅ Création de studios privés</li>
                                <li class="list-group-item">✅ Commandes artistiques interactives</li>
                            </ul>
                            
                            <h4>Messages de Bienvenue</h4>
                            <div class="mb-3">
                                Canal de Bienvenue configuré: <code>ID 1356985323313172682</code>
                            </div>
                            
                            <h4 class="mt-4">Surveillance du Bot</h4>
                            <p>Le bot est actuellement connecté à Discord et écoute les événements sur le serveur Le Séminaire.</p>
                            
                            <div class="d-grid gap-2 mt-4">
                                <a href="#" class="btn btn-primary">Tableau de Bord Complet</a>
                                <a href="#" class="btn btn-secondary">Documentation</a>
                            </div>
                        </div>
                        <div class="card-footer text-muted">
                            LeSéminaire[BOT] - Assistant pour Communautés Artistiques
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

# Importez les modèles après la création de db
if __name__ == "__main__":
    with app.app_context():
        # import models
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)