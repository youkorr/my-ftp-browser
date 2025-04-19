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
    
    def download_file(self, path):
        """Télécharger un fichier et le retourner comme bytes."""
        try:
            # Mode passif
            data_socket, _ = self._enter_passive_mode()
            if not data_socket:
                raise Exception("Échec du mode passif")
            
            # Commande RETR
            self._send_command(f"RETR {path}")
            response = self._read_response()
            if not response.startswith('150'):
                logger.error(f"Échec de récupération du fichier : {response}")
                data_socket.close()
                raise Exception(f"Échec de récupération : {response}")
            
            # Téléchargement du fichier en mémoire
            file_data = io.BytesIO()
            while True:
                chunk = data_socket.recv(8192)
                if not chunk:
                    break
                file_data.write(chunk)
            
            data_socket.close()
            
            # Attendre le message de fin de transfert
            response = self._read_response()
            if not response.startswith('226'):
                logger.warning(f"Message de fin de transfert non reçu : {response}")
            
            file_data.seek(0)
            return file_data
            
        except Exception as e:
            logger.error(f"Erreur de téléchargement de fichier : {e}")
            raise
    
    def _enter_passive_mode(self):
        """Passer en mode passif et retourner le socket de données."""
        try:
            self._send_command("PASV")
            response = self._read_response()
            if not response.startswith('227'):
                logger.error(f"Échec du mode passif : {response}")
                return None, None
            
            # Parser la réponse pour extraire l'IP et le port
            match = re.search(r'(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', response)
            if not match:
                logger.error(f"Erreur de parsing de la réponse PASV : {response}")
                return None, None
                
            ip_parts = match.groups()[:4]
            port_parts = match.groups()[4:]
            
            ip = '.'.join(ip_parts)
            port = (int(port_parts[0]) << 8) + int(port_parts[1])
            
            # Créer le socket de données
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            s.connect((ip, port))
            
            return s, (ip, port)
            
        except Exception as e:
            logger.error(f"Erreur de passage en mode passif : {e}")
            return None, None

    def _send_command(self, command):
        """Envoyer une commande au serveur FTP."""
        if not self.control_socket:
            raise ConnectionError("Non connecté au serveur FTP")
            
        cmd_bytes = (command + '\r\n').encode(self.encoding)
        self.control_socket.sendall(cmd_bytes)

    def _read_response(self):
        """Lire une réponse du serveur FTP."""
        if not self.control_socket:
            raise ConnectionError("Non connecté au serveur FTP")
            
        response_lines = []
        
        while True:
            line = b''
            while not line.endswith(b'\r\n'):
                chunk = self.control_socket.recv(1)
                if not chunk:
                    break
                line += chunk
            
            line_str = line.decode(self.encoding).strip()
            response_lines.append(line_str)
            
            # Vérifier si la réponse multi-ligne est complète
            if line_str[:3].isdigit() and line_str[3:4] == ' ':
                break
        
        return '\n'.join(response_lines)

    def _format_size(self, size_bytes):
        """Formater la taille en Ko, Mo, Go."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024*1024:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024*1024*1024:
            return f"{size_bytes/(1024*1024):.1f} MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.1f} GB"
        
    def close(self):
        """Fermer la connexion."""
        try:
            if self.control_socket:
                try:
                    self._send_command("QUIT")
                    self._read_response()
                except Exception:
                    pass
                finally:
                    self.control_socket.close()
                    self.control_socket = None
        except Exception as e:
            logger.error(f"Erreur de fermeture de connexion FTP : {e}")

# Gestion des partages
def load_shares():
    """Charger les partages existants."""
    shares_file = os.path.join(SHARES_DIR, "shares.json")
    if not os.path.exists(shares_file):
        return {}
    
    try:
        with open(shares_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erreur de chargement des partages : {e}")
        return {}

def save_shares(shares):
    """Sauvegarder les partages."""
    shares_file = os.path.join(SHARES_DIR, "shares.json")
    
    # Créer le répertoire si nécessaire
    if not os.path.exists(SHARES_DIR):
        os.makedirs(SHARES_DIR)
    
    try:
        with open(shares_file, 'w') as f:
            json.dump(shares, f)
    except Exception as e:
        logger.error(f"Erreur de sauvegarde des partages : {e}")

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

# Routes API
@app.route('/servers', methods=['GET'])
def get_servers():
    """Obtenir la liste des serveurs FTP configurés."""
    try:
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
    except Exception as e:
        logger.error(f"Erreur de lecture des serveurs : {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/browse/<int:server_id>', methods=['GET'])
def browse_server(server_id):
    """Parcourir un serveur FTP."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        servers = config.get('ftp_servers', [])
        if server_id >= len(servers):
            return jsonify({'error': 'Serveur non trouvé'}), 404
        
        server = servers[server_id]
        path = request.args.get('path', '/')
        
        # Si un chemin racine est défini, l'utiliser
        root_path = server.get('root_path', '')
        if root_path and path == '/':
            actual_path = root_path
        elif root_path:
            actual_path = os.path.join(root_path, path.lstrip('/'))
        else:
            actual_path = path
        
        client = FTPClient(server['host'], server['port'])
        
        if client.connect() and client.login(server['username'], server['password']):
            files = client.list_directory(actual_path)
            client.close()
            
            # Transformer les chemins pour les rendre relatifs à la racine virtuelle
            if root_path:
                for file in files:
                    file_path = file['path']
                    if file_path.startswith(root_path):
                        relative_path = file_path[len(root_path):]
                        if not relative_path.startswith('/'):
                            relative_path = '/' + relative_path
                        file['path'] = relative_path
            
            return jsonify({
                'server_name': server['name'],
                'current_path': path,
                'files': files
            })
        else:
            return jsonify({'error': 'Échec de connexion au serveur FTP'}), 500
    except Exception as e:
        logger.error(f"Erreur de navigation FTP : {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<int:server_id>', methods=['GET'])
def download_file(server_id):
    """Télécharger un fichier depuis le serveur FTP."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        servers = config.get('ftp_servers', [])
        if server_id >= len(servers):
            return jsonify({'error': 'Serveur non trouvé'}), 404
        
        server = servers[server_id]
        path = request.args.get('path', '')
        
        if not path:
            return jsonify({'error': 'Chemin non spécifié'}), 400
        
        # Si un chemin racine est défini, l'utiliser
        root_path = server.get('root_path', '')
        if root_path:
            actual_path = os.path.join(root_path, path.lstrip('/'))
        else:
            actual_path = path
        
        filename = os.path.basename(path)
        
        client = FTPClient(server['host'], server['port'])
        
        if client.connect() and client.login(server['username'], server['password']):
            try:
                file_data = client.download_file(actual_path)
                client.close()
                
                return send_file(
                    file_data,
                    as_attachment=True,
                    attachment_filename=filename,
                    mimetype='application/octet-stream'
                )
            except Exception as e:
                client.close()
                logger.error(f"Erreur de téléchargement : {e}")
                return jsonify({'error': f'Erreur de téléchargement: {str(e)}'}), 500
        else:
            return jsonify({'error': 'Échec de connexion au serveur FTP'}), 500
    except Exception as e:
        logger.error(f"Erreur de téléchargement : {e}")
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
        
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        servers = config.get('ftp_servers', [])
        if server_id >= len(servers):
            return jsonify({'error': 'Serveur non trouvé'}), 404
        
        server = servers[server_id]
        
        # Si un chemin racine est défini, l'utiliser
        root_path = server.get('root_path', '')
        if root_path:
            actual_path = os.path.join(root_path, path.lstrip('/'))
        else:
            actual_path = path
        
        # Créer un token unique
        token = str(uuid.uuid4())
        
        # Enregistrer le partage
        shares = load_shares()
        expiry = time.time() + (duration * 3600)
        
        shares[token] = {
            'server_id': server_id,
            'path': actual_path,
            'display_path': path,
            'expiry': expiry,
            'created': time.time(),
            'server_name': server['name'],
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
        logger.error(f"Erreur de création de partage : {e}")
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
        logger.error(f"Erreur de listage des partages : {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/shares/<token>', methods=['DELETE'])
def delete_share(token):
    """Supprimer un partage."""
    try:
        shares = load_shares()
        
        if token in shares:
            del shares[token]
            save_shares(shares)
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Partage non trouvé'}), 404
    except Exception as e:
        logger.error(f"Erreur de suppression de partage : {e}")
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
        
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        servers = config.get('ftp_servers', [])
        if server_id >= len(servers):
            return jsonify({'error': 'Serveur non trouvé'}), 404
        
        server = servers[server_id]
        
        client = FTPClient(server['host'], server['port'])
        
        if client.connect() and client.login(server['username'], server['password']):
            try:
                file_data = client.download_file(path)
                client.close()
                
                return send_file(
                    file_data,
                    as_attachment=True,
                    attachment_filename=filename,
                    mimetype='application/octet-stream'
                )
            except Exception as e:
                client.close()
                logger.error(f"Erreur de téléchargement de fichier partagé : {e}")
                return jsonify({'error': f'Erreur de téléchargement: {str(e)}'}), 500
        else:
            return jsonify({'error': 'Échec de connexion au serveur FTP'}), 500
    except Exception as e:
        logger.error(f"Erreur de téléchargement de fichier partagé : {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/schedule', methods=['POST'])
def schedule_share():
    """Planifier un partage avec des options avancées."""
    try:
        data = request.json
        server_id = data.get('server_id')
        path = data.get('path')
        schedule = data.get('schedule', {})
        
        if not server_id or not path:
            return jsonify({'error': 'Paramètres manquants'}), 400
        
        # Paramètres de planification
        start_time = schedule.get('start_time')  # Timestamp Unix
        end_time = schedule.get('end_time')  # Timestamp Unix
        days = schedule.get('days', [])  # [0-6] Lundi à Dimanche
        
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        servers = config.get('ftp_servers', [])
        if server_id >= len(servers):
            return jsonify({'error': 'Serveur non trouvé'}), 404
        
        server = servers[server_id]
        
        # Si un chemin racine est défini, l'utiliser
        root_path = server.get('root_path', '')
        if root_path:
            actual_path = os.path.join(root_path, path.lstrip('/'))
        else:
            actual_path = path
        
        # Créer un token unique
        token = str(uuid.uuid4())
        
        # Enregistrer le partage planifié
        shares = load_shares()
        
        # Calculer l'expiration (utiliser end_time si défini, sinon un an)
        if end_time:
            expiry = end_time
        else:
            expiry = time.time() + (365 * 24 * 3600)  # Un an par défaut
        
        shares[token] = {
            'server_id': server_id,
            'path': actual_path,
            'display_path': path,
            'expiry': expiry,
            'created': time.time(),
            'server_name': server['name'],
            'filename': os.path.basename(path),
            'scheduled': True,
            'schedule': {
                'start_time': start_time,
                'end_time': end_time,
                'days': days
            }
        }
        
        save_shares(shares)
        
        # URL de partage
        share_url = f"/api/download/{token}"
        
        return jsonify({
            'token': token,
            'url': share_url,
            'expiry': expiry,
            'schedule': schedule,
            'expiry_human': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expiry))
        })
    except Exception as e:
        logger.error(f"Erreur de planification de partage : {e}")
        return jsonify({'error': str(e)}), 500

# Nettoyage périodique des partages expirés
def periodic_cleanup():
    """Effectuer un nettoyage périodique."""
    while True:
        time.sleep(3600)  # Toutes les heures
        clean_expired_shares()

# Démarrer le thread de nettoyage
cleanup_thread = threading.Thread(target=periodic_cleanup)
cleanup_thread.daemon = True
cleanup_thread.start()

# Démarrer le serveur
if __name__ == "__main__":
    logger.info("=== Démarrage du serveur FTP Browser ===")
    try:
        run_simple(
            hostname='127.0.0.1',
            port=5000,
            application=app,
            use_reloader=False,
            threaded=True
        )
    except Exception as e:
        logger.critical(f"Échec du démarrage: {str(e)}")
        exit(1)






















