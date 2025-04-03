#!/bin/bash
echo "===================================="
echo "Lancement de LeSéminaire[BOT]"
echo "===================================="

# Fonction pour vérifier si le bot Discord est en cours d'exécution
check_discord_bot() {
    pgrep -f "python bot_launcher.py" > /dev/null
    return $?
}

# Fonction pour vérifier si l'application web est en cours d'exécution sur le port 8080
check_web_app_8080() {
    pgrep -f "python main.py web8080" > /dev/null
    return $?
}

# Fonction pour vérifier si l'application web est en cours d'exécution sur le port 5000
check_web_app_5000() {
    pgrep -f "gunicorn --bind 0.0.0.0:5000" > /dev/null
    return $?
}

# Démarrage du bot Discord s'il n'est pas déjà en cours d'exécution
if ! check_discord_bot; then
    echo "Démarrage du bot Discord..."
    python bot_launcher.py &
    sleep 2
else
    echo "Le bot Discord est déjà en cours d'exécution."
fi

# Démarrage de l'application web sur le port 8080 si elle n'est pas déjà en cours d'exécution
if ! check_web_app_8080 && ! check_web_app_5000; then
    echo "Démarrage de l'application web sur le port 8080..."
    python main.py web8080 &
    sleep 2
else
    if check_web_app_5000; then
        echo "L'application web est déjà en cours d'exécution sur le port 5000."
    else
        echo "L'application web est déjà en cours d'exécution sur le port 8080."
    fi
fi

echo "===================================="
echo "Services démarrés"
echo "Bot Discord: En cours d'exécution"
if check_web_app_5000; then
    echo "Application web: Disponible sur http://localhost:5000"
else
    echo "Application web: Disponible sur http://localhost:8080"
fi
echo "===================================="
echo "Utilisez CTRL+C pour arrêter les services."

# Maintenir le script actif pour permettre aux services de continuer à s'exécuter
wait