#!/usr/bin/env python3
"""API FTP Browser pour Home Assistant."""
import os
import json
import time
import socket
import uuid
import re
import logging
from flask import Flask, request, jsonify, send_file, Response
from werkzeug.serving import run_simple
import threading
import io

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ftp-browser")

app = Flask(__name__)

# Charger la configuration
CONFIG_FILE = "/etc/ftpbrowser/server.json"
SHARES_DIR = "/data/ftpbrowser/shares"

# Client FTP
class FTPClient:
    """Client FTP direct."""
    def __init__(self, host, port=21, timeout=15):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.control_socket = None
        self.encoding = 'utf-8'
        
    def connect(self):
        """Se connecter au serveur FTP."""
        try:
            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.control_socket.settimeout(self.timeout)
            self.control_socket.connect((self.host, self.port))
            
            # Lire le message de bienvenue
            response = self._read_response()
            if not response.startswith('220'):
                logger.error(f"Message de bienvenue FTP non reçu : {response}")
                self.close()
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur de connexion FTP : {e}")
            self.close()
            return False

    def login(self, username, password):
        """S'authentifier au serveur FTP."""
        try:
            # Envoyer le nom d'utilisateur
            self._send_command(f"USER {username}")
            response = self._read_response()
            if not (response.startswith('230') or response.startswith('331')):
                logger.error(f"Échec d'authentification (nom d'utilisateur) : {response}")
                return False
            
            # Envoyer le mot de passe si nécessaire
            if response.startswith('331'):
                self._send_command(f"PASS {password}")
                response = self._read_response()
                if not response.startswith('230'):
                    logger.error(f"Échec d'authentification (mot de passe) : {response}")
                    return False
            
            # Mode binaire
            self._send_command("TYPE I")
            response = self._read_response()
            if not response.startswith('200'):
                logger.error(f"Échec de configuration du mode binaire : {response}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Erreur d'authentification FTP : {e}")
            return False
            
    def list_directory(self, path='/'):
        """Lister le contenu d'un répertoire."""
        try:
            if path != '/':
                self._send_command(f"CWD {path}")
                response = self._read_response()
                if not response.startswith('250'):
                    logger.error(f"Échec de changement de répertoire : {response}")
                    return []
            
            # Mode passif
            data_socket, _ = self._enter_passive_mode()
            if not data_socket:
                return []
            
            # Commande LIST
            self._send_command("LIST -la")
            response = self._read_response()
            if not (response.startswith('150') or response.startswith('125')):
                logger.error(f"Échec de listage du répertoire : {response}")
                data_socket.close()
                return []
            
            # Lecture du listage
            listing_data = b''
            while True:
                chunk = data_socket.recv(1024)
                if not chunk:
                    break
                listing_data += chunk
            
            data_socket.close()
            
            # Attendre le message de fin de transfert
            response = self._read_response()
            if not response.startswith('226'):
                logger.warning(f"Message de fin de transfert non reçu : {response}")
            
            # Parser le listage
            files = []
            for line in listing_data.decode(self.encoding).splitlines():
                if not line.strip():
                    continue
                    
                try:
                    parts = line.split(None, 8)
                    if len(parts) < 9:
                        continue
                        
                    perms = parts[0]
                    size = int(parts[4]) if parts[4].isdigit() else 0
                    name = parts[8]
                    
                    # Ignorer . et .. 
                    if name in ('.', '..'):
                        continue
                        
                    is_dir = perms.startswith('d')
                    
                    file_path = os.path.join(path, name)
                    if path == '/':
                        file_path = '/' + name
                    
                    files.append({
                        'name': name,
                        'path': file_path,
                        'type': 'directory' if is_dir else 'file',
                        'size': size,
                        'size_human': self._format_size(size),
                        'permissions': perms,
                        'is_directory': is_dir
                    })
                except Exception as e:
                    logger.warning(f"Erreur d'analyse d'élément FTP '{line}' : {e}")
            
            return files
            
        except Exception as e:
            logger.error(f"Erreur de listage de répertoire : {e}")
            return []





















