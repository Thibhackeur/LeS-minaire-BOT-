"""
Script pour lancer l'application web sur un port spécifique.
Utilisé pour éviter les conflits de port avec l'application Discord.
"""
import os
from app import app

if __name__ == "__main__":
    # Démarrer l'application Flask sur le port 8080
    port = int(os.environ.get('PORT', 8080))
    print(f"Démarrage de l'application web sur http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)