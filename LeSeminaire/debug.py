"""
Script pour lancer l'application Flask en mode de débogage
"""
from app import app, db
import models

# Initialiser l'application
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        
        # Vérifier si un administrateur existe, sinon en créer un
        admin = db.session.query(models.Admin).first()
        if not admin:
            print("Création d'un compte administrateur par défaut...")
            admin = models.Admin(
                username="admin",
                email="admin@leseminaire.com"
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Compte administrateur créé avec succès!")
    
    # Lancer l'application en mode debug
    app.run(host="0.0.0.0", port=8080, debug=True)