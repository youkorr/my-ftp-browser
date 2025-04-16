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

def load_json_file(file_path, default_value=None):
    """Charge un fichier JSON avec gestion robuste des erreurs."""
    if default_value is None:
        default_value = {}
    
    try:
        if not os.path.exists(file_path):
            return default_value
            
        with open(file_path, 'r') as f:
            content = f.read().strip()
            if not content:
                return default_value
            return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de décodage JSON dans {file_path}: {e}")
        return default_value
    except Exception as e:
        logger.error(f"Erreur de lecture de {file_path}: {e}")
        return default_value

def save_json_file(file_path, data):
    """Sauvegarde des données dans un fichier JSON."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Erreur d'écriture dans {file_path}: {e}")
        return False

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
            self._send_command(f"USER {username}")
            response = self._read_response()
            if not (response.startswith('230') or response.startswith('331')):
                logger.error(f"Échec d'authentification (nom d'utilisateur) : {response}")
                return False
            
            if response.startswith('331'):
                self._send_command(f"PASS {password}")
                response = self._read_response()
                if not response.startswith('230'):
                    logger.error(f"Échec d'authentification (mot de passe) : {response}")
                    return False
            
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
            
            data_socket, _ = self._enter_passive_mode()
            if not data_socket:
                return []
            
            self._send_command("LIST -la")
            response = self._read_response()
            if not (response.startswith('150') or response.startswith('125')):
                logger.error(f"Échec de listage du répertoire : {response}")
                data_socket.close()
                return []
            
            listing_data = b''
            while True:
                chunk = data_socket.recv(1024)
                if not chunk:
                    break
                listing_data += chunk
            
            data_socket.close()
            
            response = self._read_response()
            if not response.startswith('226'):
                logger.warning(f"Message de fin de transfert non reçu : {response}")
            
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
            data_socket, _ = self._enter_passive_mode()
            if not data_socket:
                raise Exception("Échec du mode passif")
            
            self._send_command(f"RETR {path}")
            response = self._read_response()
            if not response.startswith('150'):
                logger.error(f"Échec de récupération du fichier : {response}")
                data_socket.close()
                raise Exception(f"Échec de récupération : {response}")
            
            file_data = io.BytesIO()
            while True:
                chunk = data_socket.recv(8192)
                if not chunk:
                    break
                file_data.write(chunk)
            
            data_socket.close()
            
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
            
            match = re.search(r'(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', response)
            if not match:
                logger.error(f"Erreur de parsing de la réponse PASV : {response}")
                return None, None
                
            ip = '.'.join(match.groups()[:4])
            port = (int(match.groups()[4]) << 8) + int(match.groups()[5])
            
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
            
        self.control_socket.sendall((command + '\r\n').encode(self.encoding))

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
    return load_json_file(os.path.join(SHARES_DIR, "shares.json"), {})

def save_shares(shares):
    """Sauvegarder les partages."""
    save_json_file(os.path.join(SHARES_DIR, "shares.json"), shares)

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
        config = load_json_file(CONFIG_FILE, {"ftp_servers": []})
        
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
        config = load_json_file(CONFIG_FILE, {"ftp_servers": []})
        servers = config.get('ftp_servers', [])
        
        if server_id >= len(servers):
            return jsonify({'error': 'Serveur non trouvé'}), 404
        
        server = servers[server_id]
        path = request.args.get('path', '/')
        
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
        config = load_json_file(CONFIG_FILE, {"ftp_servers": []})
        servers = config.get('ftp_servers', [])
        
        if server_id >= len(servers):
            return jsonify({'error': 'Serveur non trouvé'}), 404
        
        server = servers[server_id]
        path = request.args.get('path', '')
        
        if not path:
            return jsonify({'error': 'Chemin non spécifié'}), 400
        
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
                    download_name=filename,
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
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON manquantes ou invalides'}), 400
            
        server_id = data.get('server_id')
        path = data.get('path')
        duration = data.get('duration', 24)
        
        if server_id is None or not path:
            return jsonify({'error': 'Paramètres manquants'}), 400
        
        config = load_json_file(CONFIG_FILE, {"ftp_servers": []})
        servers = config.get('ftp_servers', [])
        
        if server_id >= len(servers):
            return jsonify({'error': 'Serveur non trouvé'}), 404
        
        server = servers[server_id]
        
        root_path = server.get('root_path', '')
        if root_path:
            actual_path = os.path.join(root_path, path.lstrip('/'))
        else:
            actual_path = path
        
        token = str(uuid.uuid4())
        expiry = time.time() + (duration * 3600)
        
        shares = load_shares()
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
        
        config = load_json_file(CONFIG_FILE, {"ftp_servers": []})
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
                    download_name=filename,
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

# Nettoyage périodique des partages expirés
def periodic_cleanup():
    """Effectuer un nettoyage périodique."""
    while True:
        time.sleep(3600)
        clean_expired_shares()

# Démarrer le thread de nettoyage
cleanup_thread = threading.Thread(target=periodic_cleanup)
cleanup_thread.daemon = True
cleanup_thread.start()

# Démarrer le serveur
if __name__ == "__main__":
    if not os.path.exists(SHARES_DIR):
        os.makedirs(SHARES_DIR)
        
    clean_expired_shares()
    
    logger.info("Démarrage du serveur API FTP Browser")
    run_simple('0.0.0.0', 5000, app, use_reloader=False)

