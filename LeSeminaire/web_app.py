"""
Point d'entrée spécifique pour l'application web Flask.
Ce fichier démarre l'application web sur le port 8080 pour éviter les conflits avec le bot Discord.
"""
import os
from app import app

if __name__ == "__main__":
    # Démarrer l'application Flask sur le port 8080
    port = int(os.environ.get('PORT', 8080))
    print(f"Démarrage de l'application web sur http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)