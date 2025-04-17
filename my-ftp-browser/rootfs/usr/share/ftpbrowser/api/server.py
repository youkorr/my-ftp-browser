#!/usr/bin/env python3
"""API FTP Browser pour Home Assistant."""
import os
import json
import time
import logging
import ftplib
import uuid
from flask import Flask, request, jsonify, send_file
import io
import threading

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ftp-browser")

app = Flask(__name__)

# Chemins de configuration
CONFIG_FILE = "/etc/ftpbrowser/server.json"
SHARES_DIR = "/data/ftpbrowser/shares"

class FTPClientWrapper:
    """Classe pour gérer les connexions FTP de manière simple."""
    
    def __init__(self, server_info):
        """Initialiser avec les informations du serveur."""
        self.host = server_info.get('host', '')
        self.port = server_info.get('port', 21)
        self.username = server_info.get('username', '')
        self.password = server_info.get('password', '')
        self.root_path = server_info.get('root_path', '/')
        self.passive = server_info.get('passive', True)
        self.timeout = server_info.get('timeout', 30)
        self.client = None

    def connect(self):
        """Se connecter au serveur FTP."""
        try:
            # Créer le client
            self.client = ftplib.FTP()
            self.client.set_debuglevel(0)  # 0 pour désactiver, 1 pour activer le debug
            
            # Définir le timeout
            self.client.timeout = self.timeout
            
            # Se connecter
            logger.info(f"Connexion à {self.host}:{self.port}")
            self.client.connect(self.host, self.port)
            
            # S'authentifier
            logger.info(f"Login avec l'utilisateur {self.username}")
            self.client.login(self.username, self.password)
            
            # Définir le mode passif
            if self.passive:
                self.client.set_pasv(True)
                
            logger.info("Connexion FTP réussie")
            return True
        except Exception as e:
            logger.error(f"Erreur de connexion FTP: {e}")
            self.close()
            return False
    
    def list_directory(self, path='/'):
        """Lister le contenu d'un répertoire."""
        if not self.client:
            if not self.connect():
                return []
                
        try:
            # Ajuster le chemin avec le chemin racine si nécessaire
            actual_path = self._adjust_path(path)
            logger.info(f"Listage du répertoire FTP: {actual_path}")
            
            # Lister les fichiers et dossiers
            files = []
            
            # Obtenir la liste des fichiers et dossiers
            file_list = []
            self.client.cwd(actual_path)
            self.client.dir('.', lambda x: file_list.append(x))
            
            # Parser les entrées
            for line in file_list:
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
                
                # Construire le chemin
                if path == '/':
                    file_path = '/' + name
                else:
                    file_path = os.path.join(path, name)
                
                # Ajouter l'entrée
                files.append({
                    'name': name,
                    'path': file_path,
                    'type': 'directory' if is_dir else 'file',
                    'size': size,
                    'size_human': self._format_size(size),
                    'is_directory': is_dir
                })
                
            return files
        except Exception as e:
            logger.error(f"Erreur lors du listage FTP: {e}")
            # Essayer de se reconnecter une fois en cas d'erreur
            self.close()
            if self.connect():
                try:
                    # Réessayer l'opération
                    actual_path = self._adjust_path(path)
                    file_list = []
                    self.client.cwd(actual_path)
                    self.client.dir('.', lambda x: file_list.append(x))
                    
                    # Même code de parsing que ci-dessus...
                    files = []
                    # [...]
                    
                    return files
                except Exception as e2:
                    logger.error(f"Échec de la seconde tentative: {e2}")
            
            return []
    
    def download_file(self, path):
        """Télécharger un fichier depuis le serveur FTP."""
        if not self.client:
            if not self.connect():
                raise Exception("Impossible de se connecter au serveur FTP")
                
        try:
            # Ajuster le chemin avec le chemin racine si nécessaire
            actual_path = self._adjust_path(path)
            logger.info(f"Téléchargement du fichier FTP: {actual_path}")
            
            # Créer un buffer en mémoire pour recevoir le fichier
            buffer = io.BytesIO()
            
            # Télécharger le fichier
            self.client.retrbinary(f'RETR {actual_path}', buffer.write)
            
            # Rembobiner le buffer
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement FTP: {e}")
            # Essayer de se reconnecter et de réessayer
            self.close()
            if self.connect():
                try:
                    buffer = io.BytesIO()
                    actual_path = self._adjust_path(path)
                    self.client.retrbinary(f'RETR {actual_path}', buffer.write)
                    buffer.seek(0)
                    return buffer
                except Exception as e2:
                    logger.error(f"Échec de la seconde tentative: {e2}")
            
            raise Exception(f"Impossible de télécharger le fichier: {e}")
    
    def _adjust_path(self, path):
        """Ajuster le chemin avec le chemin racine."""
        if not self.root_path or self.root_path == '/':
            return path
            
        if path == '/':
            return self.root_path
            
        # Enlever le slash initial de path pour éviter un double slash
        path_no_slash = path.lstrip('/')
        
        # Construire le chemin complet
        if self.root_path.endswith('/'):
            return f"{self.root_path}{path_no_slash}"
        else:
            return f"{self.root_path}/{path_no_slash}"
    
    def _format_size(self, size_bytes):
        """Formater la taille en unités lisibles."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
    
    def close(self):
        """Fermer la connexion FTP."""
        if self.client:
            try:
                self.client.quit()
            except:
                try:
                    self.client.close()
                except:
                    pass
            finally:
                self.client = None

# Fonctions pour gérer les partages
def load_shares():
    """Charger les partages existants."""
    shares_file = os.path.join(SHARES_DIR, "shares.json")
    if not os.path.exists(shares_file):
        return {}
    
    try:
        with open(shares_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erreur lors du chargement des partages: {e}")
        return {}

def save_shares(shares):
    """Sauvegarder les partages."""
    # Assurer que le dossier existe
    if not os.path.exists(SHARES_DIR):
        os.makedirs(SHARES_DIR, exist_ok=True)
        
    shares_file = os.path.join(SHARES_DIR, "shares.json")
    
    try:
        with open(shares_file, 'w') as f:
            json.dump(shares, f)
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement des partages: {e}")

def clean_expired_shares():
    """Nettoyer les partages expirés."""
    shares = load_shares()
    now = time.time()
    expired = []
    
    for token, share in list(shares.items()):
        if share.get('expiry', 0) < now:
            expired.append(token)
            del shares[token]
    
    if expired:
        logger.info(f"Nettoyage de {len(expired)} partages expirés")
        save_shares(shares)

# Fonction pour obtenir les informations d'un serveur
def get_server_info(server_id):
    """Obtenir les informations d'un serveur à partir de son ID."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            
            servers = config.get('ftp_servers', [])
            if 0 <= server_id < len(servers):
                return servers[server_id]
        
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du serveur {server_id}: {e}")
        return None

# Routes API
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
        logger.error(f"Erreur de lecture des serveurs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/browse/<int:server_id>', methods=['GET'])
def browse_server(server_id):
    """Parcourir un serveur FTP."""
    try:
        server_info = get_server_info(server_id)
        if not server_info:
            return jsonify({'error': 'Serveur non trouvé'}), 404
            
        path = request.args.get('path', '/')
        
        # Créer le client FTP
        client = FTPClientWrapper(server_info)
        
        # Lister les fichiers
        files = client.list_directory(path)
        
        # Fermer la connexion
        client.close()
        
        return jsonify({
            'server_name': server_info['name'],
            'current_path': path,
            'files': files
        })
    
    except Exception as e:
        logger.error(f"Erreur lors du parcours du serveur {server_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<int:server_id>', methods=['GET'])
def download_file(server_id):
    """Télécharger un fichier depuis le serveur FTP."""
    try:
        server_info = get_server_info(server_id)
        if not server_info:
            return jsonify({'error': 'Serveur non trouvé'}), 404
            
        path = request.args.get('path', '')
        if not path:
            return jsonify({'error': 'Chemin non spécifié'}), 400
            
        filename = os.path.basename(path)
        
        # Créer le client FTP
        client = FTPClientWrapper(server_info)
        
        # Télécharger le fichier
        buffer = client.download_file(path)
        
        # Fermer la connexion
        client.close()
        
        return send_file(
            buffer,
            as_attachment=True,
            attachment_filename=filename,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement depuis {server_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/share', methods=['POST'])
def create_share():
    """Créer un lien de partage."""
    try:
        data = request.json
        server_id = data.get('server_id')
        path = data.get('path')
        duration = data.get('duration', 24)  # Heures
        
        if server_id is None or not path:
            return jsonify({'error': 'Paramètres manquants'}), 400
            
        server_info = get_server_info(server_id)
        if not server_info:
            return jsonify({'error': 'Serveur non trouvé'}), 404
            
        # Créer un token unique
        token = str(uuid.uuid4())
        
        # Enregistrer le partage
        shares = load_shares()
        expiry = time.time() + (duration * 3600)
        
        shares[token] = {
            'server_id': server_id,
            'path': path,
            'expiry': expiry,
            'created': time.time(),
            'server_name': server_info['name'],
            'filename': os.path.basename(path)
        }
        
        save_shares(shares)
        
        # URL de partage
        share_url = f"/api/download/{token}"
        
        return jsonify({
            'token': token,
            'url': share_url,
            'expiry': expiry,
            'expiry_human': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expiry))
        })
    except Exception as e:
        logger.error(f"Erreur lors de la création d'un partage: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/shares', methods=['GET'])
def list_shares():
    """Lister les partages actifs."""
    try:
        shares = load_shares()
        now = time.time()
        
        # Filtrer les partages expirés
        active_shares = {}
        for token, share in shares.items():
            if share.get('expiry', 0) > now:
                active_shares[token] = share
        
        return jsonify({
            'shares': active_shares,
            'count': len(active_shares)
        })
    except Exception as e:
        logger.error(f"Erreur lors du listage des partages: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<token>', methods=['GET'])
def download_shared(token):
    """Télécharger un fichier partagé."""
    try:
        shares = load_shares()
        
        if token not in shares:
            return jsonify({'error': 'Lien de partage invalide'}), 404
        
        share = shares[token]
        now = time.time()
        
        if share.get('expiry', 0) < now:
            return jsonify({'error': 'Lien de partage expiré'}), 410
        
        server_id = share['server_id']
        path = share['path']
        filename = share['filename']
        
        server_info = get_server_info(server_id)
        if not server_info:
            return jsonify({'error': 'Serveur non trouvé'}), 404
            
        # Créer le client FTP
        client = FTPClientWrapper(server_info)
        
        # Télécharger le fichier
        buffer = client.download_file(path)
        
        # Fermer la connexion
        client.close()
        
        return send_file(
            buffer,
            as_attachment=True,
            attachment_filename=filename,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement d'un fichier partagé: {e}")
        return jsonify({'error': str(e)}), 500

# Nettoyage périodique des partages expirés
def periodic_cleanup():
    """Effectuer un nettoyage périodique."""
    while True:
        try:
            time.sleep(3600)  # Toutes les heures
            clean_expired_shares()
        except Exception as e:
            logger.error(f"Erreur dans le nettoyage périodique: {e}")

# Vérification de l'état
@app.route('/health', methods=['GET'])
def health_check():
    """Vérifier l'état de l'API."""
    return jsonify({'status': 'healthy', 'time': time.time()})

# Démarrer le serveur
if __name__ == "__main__":
    # S'assurer que les dossiers existent
    os.makedirs(SHARES_DIR, exist_ok=True)
        
    # Nettoyer les partages expirés au démarrage
    clean_expired_shares()
    
    # Démarrer le thread de nettoyage
    cleanup_thread = threading.Thread(target=periodic_cleanup)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    logger.info("Démarrage du serveur API FTP Browser sur 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)























