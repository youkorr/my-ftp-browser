#!/usr/bin/env python3
"""API FTP Browser pour Home Assistant."""
import os
import json
import time
import logging
from flask import Flask, request, jsonify, Response

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ftpbrowser")

app = Flask(__name__)

# Configuration
CONFIG_PATH = "/data/options.json"
CACHE_PATH = "/config/ftp_cache.json"

@app.route('/')
def index():
    """Route principale."""
    return jsonify({
        "status": "online",
        "message": "FTP Browser API is running"
    })

@app.route('/servers')
def get_servers():
    """Obtenir la liste des serveurs configurés."""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                
            # Masquer les mots de passe dans la réponse
            servers = []
            for i, server in enumerate(config.get('ftp_servers', [])):
                servers.append({
                    'id': i,
                    'name': server.get('name', f'Server {i}'),
                    'host': server.get('host', ''),
                    'port': server.get('port', 21),
                    'username': server.get('username', ''),
                    'root_path': server.get('root_path', '/')
                })
                
            return jsonify({"servers": servers})
        return jsonify({"servers": [], "error": "Config not found"})
    except Exception as e:
        logger.error(f"Error getting servers: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    """Vérifier l'état de l'API."""
    return jsonify({"status": "healthy", "timestamp": time.time()})

# Démarrer le serveur Flask
if __name__ == '__main__':
    logger.info("Starting FTP Browser API")
    app.run(host='0.0.0.0', port=5000)
