"""
LeSéminaire[BOT] - Lanceur dédié pour l'application web Flask
Ce fichier est exclusivement dédié au lancement de l'application web.
"""
import os
from app import app

if __name__ == "__main__":
    # Définir le port pour l'application Flask (5000 par défaut)
    port = int(os.environ.get('PORT', 5000))
    print(f"Démarrage de l'application web sur http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)