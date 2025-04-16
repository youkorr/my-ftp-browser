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

class FTPClient:
    """Client FTP optimisé avec gestion robuste des connexions."""
    def __init__(self, host, port=21, timeout=30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.control_socket = None
        self.encoding = 'utf-8'
        self.buffer_size = 8192
        
    def connect(self):
        """Connexion robuste au serveur FTP."""
        try:
            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.control_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.control_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 16384)
            self.control_socket.settimeout(10)
            
            self.control_socket.connect((self.host, self.port))
            
            response = self._read_response(timeout=10)
            if not response.startswith('220'):
                raise ConnectionError(f"Message de bienvenue invalide: {response}")
            
            self.control_socket.settimeout(None)
            return True
            
        except Exception as e:
            logger.error(f"Erreur de connexion: {str(e)}")
            self.close()
            return False

    def login(self, username, password):
        """Authentification sécurisée."""
        try:
            self._send_command(f"USER {username}")
            response = self._read_response(timeout=10)
            
            if response.startswith('331'):
                self._send_command(f"PASS {password}")
                response = self._read_response(timeout=10)
                
            if not response.startswith('230'):
                raise AuthenticationError(f"Échec authentification: {response}")
            
            # Configuration supplémentaire
            self._send_command("TYPE I")
            if not self._read_response(timeout=10).startswith('200'):
                raise ProtocolError("Échec configuration mode binaire")
                
            return True
            
        except Exception as e:
            logger.error(f"Erreur d'authentification: {str(e)}")
            return False

    def list_directory(self, path='/'):
        """Listage robuste de répertoire."""
        try:
            if path != '/':
                self._send_command(f"CWD {path}")
                if not self._read_response().startswith('250'):
                    raise ProtocolError(f"Échec changement répertoire: {path}")
            
            data_socket = self._enter_passive_mode()
            if not data_socket:
                return []
            
            self._send_command("LIST -la")
            response = self._read_response()
            if not (response.startswith('150') or response.startswith('125')):
                raise ProtocolError(f"Échec commande LIST: {response}")
            
            listing_data = self._receive_data(data_socket)
            data_socket.close()
            
            if not self._read_response().startswith('226'):
                logger.warning("Transfert incomplet")
            
            return self._parse_listing(listing_data, path)
            
        except Exception as e:
            logger.error(f"Erreur listage: {str(e)}")
            return []

    def download_file(self, path):
        """Téléchargement fiable de fichier."""
        try:
            data_socket = self._enter_passive_mode()
            if not data_socket:
                raise ConnectionError("Échec mode passif")
            
            self._send_command(f"RETR {path}")
            response = self._read_response()
            if not response.startswith('150'):
                raise ProtocolError(f"Échec RETR: {response}")
            
            file_data = self._receive_data(data_socket, binary=True)
            data_socket.close()
            
            if not self._read_response().startswith('226'):
                logger.warning("Transfert incomplet")
            
            return file_data
            
        except Exception as e:
            logger.error(f"Erreur téléchargement: {str(e)}")
            raise

    def _enter_passive_mode(self):
        """Implémentation robuste du mode passif."""
        try:
            self._send_command("PASV")
            response = self._read_response(timeout=10)
            
            if not response.startswith('227'):
                raise ProtocolError(f"Réponse PASV invalide: {response}")
            
            match = re.search(r'(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', response)
            if not match:
                raise ProtocolError("Format PASV invalide")
                
            ip = '.'.join(match.groups()[:4])
            port = (int(match.groups()[4]) << 8) + int(match.groups()[5])
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 32768)
            s.settimeout(30)
            s.connect((ip, port))
            
            return s
            
        except Exception as e:
            logger.error(f"Erreur mode passif: {str(e)}")
            return None

    def _receive_data(self, data_socket, binary=False):
        """Réception optimisée des données."""
        buffer = io.BytesIO() if binary else b''
        
        try:
            while True:
                chunk = data_socket.recv(self.buffer_size)
                if not chunk:
                    break
                    
                if binary:
                    buffer.write(chunk)
                else:
                    buffer += chunk
                    
        except socket.timeout:
            logger.warning("Timeout réception données")
        except Exception as e:
            logger.error(f"Erreur réception: {str(e)}")
            raise
            
        return buffer.getvalue() if binary else buffer

    def _parse_listing(self, listing_data, path):
        """Parsing robuste du listing FTP."""
        files = []
        for line in listing_data.decode(self.encoding).splitlines():
            try:
                parts = line.split(None, 8)
                if len(parts) < 9:
                    continue
                    
                name = parts[8]
                if name in ('.', '..'):
                    continue
                    
                is_dir = parts[0].startswith('d')
                size = int(parts[4]) if parts[4].isdigit() else 0
                full_path = os.path.join(path, name).replace('//', '/')
                
                files.append({
                    'name': name,
                    'path': full_path,
                    'type': 'directory' if is_dir else 'file',
                    'size': size,
                    'size_human': self._format_size(size),
                    'permissions': parts[0],
                    'is_directory': is_dir
                })
            except Exception as e:
                logger.warning(f"Erreur parsing ligne: {line} - {str(e)}")
                
        return files

    def _send_command(self, command):
        """Envoi sécurisé de commande."""
        if not self.control_socket:
            raise ConnectionError("Non connecté")
            
        try:
            self.control_socket.sendall((command + '\r\n').encode(self.encoding))
        except Exception as e:
            raise ConnectionError(f"Erreur envoi commande: {str(e)}")

    def _read_response(self, timeout=None):
        """Lecture robuste de réponse."""
        if timeout:
            self.control_socket.settimeout(timeout)
            
        response = []
        while True:
            try:
                line = self.control_socket.recv(1024).decode(self.encoding)
                if not line:
                    break
                    
                response.append(line.strip())
                if line[3:4] == ' ' and line[:3].isdigit():
                    break
                    
            except socket.timeout:
                logger.error("Timeout lecture réponse")
                break
            except Exception as e:
                logger.error(f"Erreur lecture: {str(e)}")
                break
                
        if timeout:
            self.control_socket.settimeout(None)
            
        return '\n'.join(response) if response else ''

    def _format_size(self, size_bytes):
        """Formatage lisible de la taille."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def close(self):
        """Fermeture sécurisée."""
        if self.control_socket:
            try:
                self._send_command("QUIT")
                self._read_response(timeout=5)
            except Exception:
                pass
            finally:
                self.control_socket.close()
                self.control_socket = None

class AuthenticationError(Exception):
    pass

class ProtocolError(Exception):
    pass

# Gestion des partages
def load_shares():
    """Charger les partages avec validation."""
    shares_file = os.path.join(SHARES_DIR, "shares.json")
    if not os.path.exists(shares_file):
        return {}
        
    try:
        with open(shares_file, 'r') as f:
            data = json.load(f)
            return {k: v for k, v in data.items() if isinstance(v, dict)}
    except Exception as e:
        logger.error(f"Erreur chargement partages: {str(e)}")
        return {}

def save_shares(shares):
    """Sauvegarde sécurisée des partages."""
    if not isinstance(shares, dict):
        raise ValueError("Shares must be a dictionary")
        
    shares_file = os.path.join(SHARES_DIR, "shares.json")
    try:
        os.makedirs(SHARES_DIR, exist_ok=True)
        with open(shares_file, 'w') as f:
            json.dump(shares, f, indent=2)
    except Exception as e:
        logger.error(f"Erreur sauvegarde partages: {str(e)}")
        raise

def clean_expired_shares():
    """Nettoyage des partages expirés."""
    shares = load_shares()
    now = time.time()
    expired = [k for k, v in shares.items() if v.get('expiry', 0) < now]
    
    if expired:
        for token in expired:
            del shares[token]
        save_shares(shares)
        logger.info(f"Nettoyé {len(expired)} partages expirés")

# Routes API
@app.route('/servers', methods=['GET'])
def get_servers():
    """Obtenir la liste des serveurs."""
    try:
        config = load_json_file(CONFIG_FILE, {"ftp_servers": []})
        servers = []
        
        for server in config.get('ftp_servers', []):
            if not isinstance(server, dict):
                continue
                
            server_copy = server.copy()
            if 'password' in server_copy:
                server_copy['password'] = '********'
            servers.append(server_copy)
            
        return jsonify({'servers': servers})
    except Exception as e:
        logger.error(f"Erreur liste serveurs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/browse/<int:server_id>', methods=['GET'])
def browse_server(server_id):
    """Navigation dans le serveur FTP."""
    try:
        config = load_json_file(CONFIG_FILE, {"ftp_servers": []})
        servers = config.get('ftp_servers', [])
        
        if server_id < 0 or server_id >= len(servers):
            return jsonify({'error': 'Serveur invalide'}), 404
            
        server = servers[server_id]
        path = request.args.get('path', '/').strip()
        
        # Construction du chemin réel
        root_path = server.get('root_path', '').strip()
        actual_path = os.path.join(root_path, path.lstrip('/')) if root_path else path
        
        client = FTPClient(server['host'], server.get('port', 21))
        
        if not client.connect() or not client.login(server['username'], server['password']):
            return jsonify({'error': 'Connexion FTP échouée'}), 500
            
        files = client.list_directory(actual_path)
        client.close()
        
        # Ajustement des chemins pour l'interface
        if root_path:
            for file in files:
                if file['path'].startswith(root_path):
                    file['path'] = file['path'][len(root_path):].lstrip('/')
                    if not file['path'].startswith('/'):
                        file['path'] = '/' + file['path']
        
        return jsonify({
            'server_name': server.get('name', 'Unknown'),
            'current_path': path,
            'files': files
        })
    except Exception as e:
        logger.error(f"Erreur navigation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<int:server_id>', methods=['GET'])
def download_file(server_id):
    """Téléchargement de fichier."""
    try:
        config = load_json_file(CONFIG_FILE, {"ftp_servers": []})
        servers = config.get('ftp_servers', [])
        
        if server_id < 0 or server_id >= len(servers):
            return jsonify({'error': 'Serveur invalide'}), 404
            
        path = request.args.get('path', '').strip()
        if not path:
            return jsonify({'error': 'Chemin requis'}), 400
            
        server = servers[server_id]
        root_path = server.get('root_path', '').strip()
        actual_path = os.path.join(root_path, path.lstrip('/')) if root_path else path
        filename = os.path.basename(path)
        
        client = FTPClient(server['host'], server.get('port', 21))
        
        if not client.connect() or not client.login(server['username'], server['password']):
            return jsonify({'error': 'Connexion FTP échouée'}), 500
            
        try:
            file_data = client.download_file(actual_path)
            client.close()
            
            return send_file(
                io.BytesIO(file_data),
                as_attachment=True,
                download_name=filename,
                mimetype='application/octet-stream'
            )
        except Exception as e:
            client.close()
            logger.error(f"Erreur téléchargement: {str(e)}")
            return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Erreur traitement: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/share', methods=['POST'])
def create_share():
    """Création de partage."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
            
        server_id = data.get('server_id')
        path = data.get('path', '').strip()
        duration = min(max(int(data.get('duration', 24)), 720)  # Limité à 30 jours
        
        if server_id is None or not path:
            return jsonify({'error': 'Paramètres manquants'}), 400
            
        config = load_json_file(CONFIG_FILE, {"ftp_servers": []})
        servers = config.get('ftp_servers', [])
        
        if server_id < 0 or server_id >= len(servers):
            return jsonify({'error': 'Serveur invalide'}), 404
            
        server = servers[server_id]
        root_path = server.get('root_path', '').strip()
        actual_path = os.path.join(root_path, path.lstrip('/')) if root_path else path
        
        token = str(uuid.uuid4())
        expiry = time.time() + (duration * 3600)
        
        shares = load_shares()
        shares[token] = {
            'server_id': server_id,
            'path': actual_path,
            'display_path': path,
            'expiry': expiry,
            'created': time.time(),
            'server_name': server.get('name', 'Unknown'),
            'filename': os.path.basename(path)
        }
        
        save_shares(shares)
        
        return jsonify({
            'token': token,
            'url': f"/api/download/{token}",
            'expiry': expiry,
            'expiry_human': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expiry))
        })
    except Exception as e:
        logger.error(f"Erreur création partage: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/shares', methods=['GET'])
def list_shares():
    """Liste des partages actifs."""
    try:
        shares = load_shares()
        now = time.time()
        active_shares = {k: v for k, v in shares.items() if v.get('expiry', 0) > now}
        
        return jsonify({
            'shares': active_shares,
            'count': len(active_shares)
        })
    except Exception as e:
        logger.error(f"Erreur listage partages: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/shares/<token>', methods=['DELETE'])
def delete_share(token):
    """Suppression de partage."""
    try:
        shares = load_shares()
        if token not in shares:
            return jsonify({'error': 'Partage non trouvé'}), 404
            
        del shares[token]
        save_shares(shares)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Erreur suppression partage: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<token>', methods=['GET'])
def download_shared(token):
    """Téléchargement via partage."""
    try:
        shares = load_shares()
        share = shares.get(token)
        
        if not share:
            return jsonify({'error': 'Partage invalide'}), 404
            
        if share.get('expiry', 0) < time.time():
            return jsonify({'error': 'Partage expiré'}), 410
            
        config = load_json_file(CONFIG_FILE, {"ftp_servers": []})
        servers = config.get('ftp_servers', [])
        server_id = share['server_id']
        
        if server_id < 0 or server_id >= len(servers):
            return jsonify({'error': 'Serveur invalide'}), 404
            
        server = servers[server_id]
        client = FTPClient(server['host'], server.get('port', 21))
        
        if not client.connect() or not client.login(server['username'], server['password']):
            return jsonify({'error': 'Connexion FTP échouée'}), 500
            
        try:
            file_data = client.download_file(share['path'])
            client.close()
            
            return send_file(
                io.BytesIO(file_data),
                as_attachment=True,
                download_name=share['filename'],
                mimetype='application/octet-stream'
            )
        except Exception as e:
            client.close()
            logger.error(f"Erreur téléchargement partagé: {str(e)}")
            return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Erreur traitement partage: {str(e)}")
        return jsonify({'error': str(e)}), 500

def load_json_file(file_path, default=None):
    """Chargement sécurisé de fichier JSON."""
    if default is None:
        default = {}
        
    try:
        if not os.path.exists(file_path):
            return default
            
        with open(file_path, 'r') as f:
            content = f.read().strip()
            if not content:
                return default
            return json.loads(content)
    except Exception as e:
        logger.error(f"Erreur chargement {file_path}: {str(e)}")
        return default

def periodic_cleanup():
    """Nettoyage périodique."""
    while True:
        time.sleep(3600)
        clean_expired_shares()

# Démarrer le thread de nettoyage
cleanup_thread = threading.Thread(target=periodic_cleanup)
cleanup_thread.daemon = True
cleanup_thread.start()

if __name__ == "__main__":
    if not os.path.exists(SHARES_DIR):
        os.makedirs(SHARES_DIR, mode=0o755, exist_ok=True)
        
    clean_expired_shares()
    
    logger.info("Démarrage du serveur API FTP Browser")
    run_simple('0.0.0.0', 5000, app, use_reloader=False)

