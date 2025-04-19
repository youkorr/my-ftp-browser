#!/usr/bin/env python3
"""API FTP Browser pour Home Assistant - Version Finale Complète"""
import os
import json
import time
import socket
import uuid
import re
import logging
from flask import Flask, request, jsonify, send_file
from werkzeug.serving import run_simple
import threading
import io
from datetime import datetime

# ==================== CONFIGURATION INITIALE ====================
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/data/ftpbrowser/server.log')
    ]
)
logger = logging.getLogger("ftp-browser")

app = Flask(__name__)

CONFIG_FILE = "/etc/ftpbrowser/server.json"
SHARES_DIR = "/data/ftpbrowser/shares"

# ==================== CLIENT FTP COMPLET ====================
class FTPClient:
    def __init__(self, host, port=21, timeout=30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.control_socket = None
        self.encoding = 'utf-8'

    def connect(self):
        try:
            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.control_socket.settimeout(self.timeout)
            self.control_socket.connect((self.host, self.port))
            response = self._read_response()
            return response.startswith('220')
        except Exception as e:
            logger.error(f"Erreur connexion: {str(e)}")
            return False

    def login(self, username, password):
        try:
            self._send_command(f"USER {username}")
            response = self._read_response()
            
            if response.startswith('230'):
                return True
            elif response.startswith('331'):
                self._send_command(f"PASS {password}")
                return self._read_response().startswith('230')
            return False
        except Exception as e:
            logger.error(f"Erreur login: {str(e)}")
            return False

    def list_directory(self, path='/'):
        try:
            if path != '/':
                self._send_command(f"CWD {path}")
                if not self._read_response().startswith('250'):
                    return []

            data_socket = self._enter_passive_mode()
            if not data_socket:
                return []

            self._send_command("LIST -la")
            if not self._read_response().startswith('150'):
                data_socket.close()
                return []

            listing_data = b''
            while True:
                chunk = data_socket.recv(4096)
                if not chunk:
                    break
                listing_data += chunk

            data_socket.close()
            self._read_response()
            return self._parse_listing(listing_data, path)
        except Exception as e:
            logger.error(f"Erreur list_directory: {str(e)}")
            return []

    def download_file(self, path):
        try:
            data_socket = self._enter_passive_mode()
            if not data_socket:
                raise Exception("Mode passif échoué")

            self._send_command(f"RETR {path}")
            if not self._read_response().startswith('150'):
                data_socket.close()
                raise Exception("Erreur RETR")

            file_data = io.BytesIO()
            while True:
                chunk = data_socket.recv(8192)
                if not chunk:
                    break
                file_data.write(chunk)

            data_socket.close()
            self._read_response()
            file_data.seek(0)
            return file_data
        except Exception as e:
            logger.error(f"Erreur download: {str(e)}")
            raise

    def _enter_passive_mode(self):
        try:
            self._send_command("PASV")
            response = self._read_response()
            if not response.startswith('227'):
                return None

            match = re.search(r'(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', response)
            if not match:
                return None

            ip = '.'.join(match.groups()[:4])
            port = (int(match.groups()[4]) << 8) + int(match.groups()[5])
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            s.connect((ip, port))
            return s
        except Exception:
            return None

    def _send_command(self, command):
        if not self.control_socket:
            raise ConnectionError("Non connecté")
        self.control_socket.sendall((command + '\r\n').encode(self.encoding))

    def _read_response(self):
        if not self.control_socket:
            raise ConnectionError("Non connecté")
        response = []
        while True:
            line = self.control_socket.recv(1024).decode(self.encoding)
            if not line:
                break
            response.append(line.strip())
            if line[3:4] == ' ':
                break
        return '\n'.join(response)

    def _parse_listing(self, listing_data, base_path):
        files = []
        for line in listing_data.decode(self.encoding).splitlines():
            if not line.strip():
                continue
            try:
                parts = re.split(r'\s+', line.strip(), 8)
                if len(parts) < 9:
                    continue

                perms = parts[0]
                size = int(parts[4]) if parts[4].isdigit() else 0
                name = parts[8]
                
                if name in ('.', '..'):
                    continue

                files.append({
                    'name': name,
                    'path': os.path.join(base_path, name).replace('//', '/'),
                    'type': 'directory' if perms.startswith('d') else 'file',
                    'size': size,
                    'permissions': perms
                })
            except Exception:
                continue
        return files

    def close(self):
        try:
            if self.control_socket:
                try:
                    self._send_command("QUIT")
                    self._read_response()
                except Exception:
                    pass
                finally:
                    self.control_socket.close()
        except Exception:
            pass

# ==================== GESTION DES PARTAGES ====================
def load_shares():
    shares_file = os.path.join(SHARES_DIR, "shares.json")
    if not os.path.exists(shares_file):
        return {}
    try:
        with open(shares_file, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_shares(shares):
    try:
        with open(os.path.join(SHARES_DIR, "shares.json"), 'w') as f:
            json.dump(shares, f)
    except Exception as e:
        logger.error(f"Erreur sauvegarde partages: {str(e)}")

def clean_expired_shares():
    shares = load_shares()
    now = time.time()
    expired = [k for k, v in shares.items() if v.get('expiry', 0) < now]
    for token in expired:
        del shares[token]
    if expired:
        save_shares(shares)

# ==================== ROUTES API COMPLÈTES ====================
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "shares_count": len(load_shares())
    })

@app.route('/api/servers', methods=['GET'])
def get_servers():
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        servers = []
        for i, server in enumerate(config.get('ftp_servers', [])):
            client = FTPClient(server['host'], server.get('port', 21))
            is_online = client.connect() and client.login(
                server.get('username', ''), 
                server.get('password', '')
            )
            client.close()

            servers.append({
                'id': i,
                'name': server['name'],
                'host': server['host'],
                'port': server.get('port', 21),
                'online': is_online
            })
            
        return jsonify({'servers': servers})
    except Exception as e:
        logger.error(f"Erreur get_servers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/browse/<int:server_id>', methods=['GET'])
def browse_server(server_id):
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        servers = config.get('ftp_servers', [])
        if server_id >= len(servers):
            return jsonify({'error': 'Serveur non trouvé'}), 404
        
        server = servers[server_id]
        path = request.args.get('path', '/')
        
        client = FTPClient(server['host'], server.get('port', 21))
        if not client.connect():
            return jsonify({'error': 'Connexion échouée'}), 502
            
        if not client.login(server.get('username', ''), server.get('password', '')):
            client.close()
            return jsonify({'error': 'Authentification échouée'}), 401

        files = client.list_directory(path)
        client.close()
        
        return jsonify({
            'path': path,
            'files': files
        })
    except Exception as e:
        logger.error(f"Erreur browse: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<int:server_id>', methods=['GET'])
def download_file(server_id):
    try:
        path = request.args.get('path', '')
        if not path:
            return jsonify({'error': 'Chemin manquant'}), 400

        with open(CONFIG_FILE, 'r') as f:
            servers = json.load(f).get('ftp_servers', [])
        
        if server_id >= len(servers):
            return jsonify({'error': 'Serveur non trouvé'}), 404

        server = servers[server_id]
        client = FTPClient(server['host'], server.get('port', 21))
        
        if not client.connect():
            return jsonify({'error': 'Connexion impossible'}), 502
            
        if not client.login(server.get('username', ''), server.get('password', '')):
            client.close()
            return jsonify({'error': 'Authentification échouée'}), 401

        file_data = client.download_file(path)
        client.close()
        return send_file(
            file_data,
            as_attachment=True,
            download_name=os.path.basename(path)
        )
    except Exception as e:
        if 'client' in locals():
            client.close()
        logger.error(f"Erreur download: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/share', methods=['POST'])
def create_share():
    try:
        data = request.json
        if not data or 'server_id' not in data or 'path' not in data:
            return jsonify({'error': 'Données invalides'}), 400

        with open(CONFIG_FILE, 'r') as f:
            servers = json.load(f).get('ftp_servers', [])
        
        if data['server_id'] >= len(servers):
            return jsonify({'error': 'Serveur invalide'}), 404

        token = str(uuid.uuid4())
        shares = load_shares()
        shares[token] = {
            'server_id': data['server_id'],
            'path': data['path'],
            'expiry': time.time() + (data.get('duration', 24) * 3600),  # Parenthèse fermante ajoutée ici
            'created': time.time()
        }
        save_shares(shares)

        return jsonify({
            'token': token,
            'url': f"/api/download/{token}"
        })
    except Exception as e:
        logger.error(f"Erreur create_share: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<token>', methods=['GET'])
def download_shared(token):
    try:
        shares = load_shares()
        if token not in shares:
            return jsonify({'error': 'Lien invalide'}), 404

        share = shares[token]
        if share['expiry'] < time.time():
            return jsonify({'error': 'Lien expiré'}), 410

        with open(CONFIG_FILE, 'r') as f:
            servers = json.load(f).get('ftp_servers', [])
        
        if share['server_id'] >= len(servers):
            return jsonify({'error': 'Serveur invalide'}), 500

        server = servers[share['server_id']]
        client = FTPClient(server['host'], server.get('port', 21))
        
        if not client.connect():
            return jsonify({'error': 'Connexion impossible'}), 502
            
        if not client.login(server.get('username', ''), server.get('password', '')):
            client.close()
            return jsonify({'error': 'Authentification échouée'}), 401

        file_data = client.download_file(share['path'])
        client.close()
        return send_file(
            file_data,
            as_attachment=True,
            download_name=os.path.basename(share['path'])
        )
    except Exception as e:
        if 'client' in locals():
            client.close()
        logger.error(f"Erreur download_shared: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== LANCEMENT DU SERVEUR ====================
def cleanup_task():
    while True:
        time.sleep(3600)
        clean_expired_shares()

if __name__ == "__main__":
    os.makedirs(SHARES_DIR, exist_ok=True)
    clean_expired_shares()
    
    threading.Thread(target=cleanup_task, daemon=True).start()
    
    logger.info("Démarrage du serveur FTP Browser")
    run_simple(
        hostname='0.0.0.0',
        port=5000,
        application=app,
        use_reloader=False,
        threaded=True
    )























