"""
LeSéminaire[BOT] - Lanceur dédié pour l'application web sur le port 8080
Ce fichier est exclusivement dédié au lancement de l'application web Flask sur le port 8080.
"""
from app import app, initialize_db

if __name__ == "__main__":
    # Initialisation de la base de données
    with app.app_context():
        initialize_db()
    
    # Démarrage de l'application web
    print("Démarrage de l'application web LeSéminaire[BOT] sur le port 8080...")
    app.run(host="0.0.0.0", port=8080, debug=True)