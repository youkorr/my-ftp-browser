#!/usr/bin/env python3
"""API FTP Browser pour Home Assistant."""
import os
import json
import time
import socket
import logging
from flask import Flask, request, jsonify, send_file, Response

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ftp-browser")

app = Flask(__name__)

# Charger la configuration
CONFIG_FILE = "/etc/ftpbrowser/server.json"
SHARES_DIR = "/data/ftpbrowser/shares"

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "FTP Browser API running"})

@app.route('/servers', methods=['GET'])
def get_servers():
    """Obtenir la liste des serveurs FTP configurés."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            
            # Ne pas renvoyer les mots de passe
            servers = []
            for server in config.get('ftp_servers', []):
                server_copy = server.copy()
                if 'password' in server_copy:
                    server_copy['password'] = '********'
                servers.append(server_copy)
                
            return jsonify({'servers': servers})
        else:
            return jsonify({'servers': [], 'error': 'Configuration file not found'})
    except Exception as e:
        logger.error(f"Error reading servers: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

# Démarrer le serveur
if __name__ == "__main__":
    # S'assurer que les dossiers existent
    if not os.path.exists(SHARES_DIR):
        os.makedirs(SHARES_DIR)
        
    logger.info("Starting FTP Browser API server")
    app.run(host='0.0.0.0', port=5000)

