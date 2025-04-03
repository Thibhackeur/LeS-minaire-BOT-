#!/bin/bash
# Script pour démarrer l'application web Flask

echo "Démarrage de l'application web sur le port 8080..."
gunicorn --bind 0.0.0.0:8080 --reuse-port --reload main:app