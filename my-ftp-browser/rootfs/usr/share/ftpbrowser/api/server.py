#!/usr/bin/env python3
"""API FTP Browser pour Home Assistant."""
import os
import json
import time
import logging
import ftplib
import socket
import uuid
from flask import Flask, request, jsonify, send_file, Response
import io
import threading
import sys

# Configuration du logger
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ftp-browser")

app = Flask(__name__)

# Chemins de configuration
CONFIG_FILE = "/etc/ftpbrowser/server.json"
SHARES_DIR = "/data/ftpbrowser/shares"

# Créer les dossiers s'ils n'existent pas
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
os.makedirs(SHARES_DIR, exist_ok=True)

class EnhancedFTP(ftplib.FTP):
    """Version améliorée de ftplib.FTP avec plus de robustesse."""
    
    def __init__(self, *args, **kwargs):
        self.encoding = kwargs.pop('encoding', 'utf-8')
        super().__init__(*args, **kwargs)
    
    def connect(self, host='', port=0, timeout=30, source_address=None):
        """Se connecter au serveur FTP avec plus d'informations de log."""
        logger.info(f"Tentative de connexion à {host}:{port} avec timeout={timeout}s")
        try:
            # Test de connexion TCP
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_socket:
                test_socket.settimeout(10)
                logger.debug(f"Test de connexion TCP à {host}:{port}")
                test_socket.connect((host, port))
                logger.debug("Test de connexion TCP réussi")
                
            # Connexion FTP
            result = super().connect(host, port, timeout, source_address)
            welcome = self.getwelcome()
            logger.info(f"Connecté au serveur FTP: {welcome}")
            return result
        except Exception as e:
            logger.error(f"Erreur de connexion à {host}:{port}: {e}")
            raise
    
    def login(self, user='', passwd='', acct=''):
        """S'authentifier avec plus d'informations de log."""
        logger.info(f"Tentative d'authentification avec l'utilisateur '{user}'")
        try:
            result = super().login(user, passwd, acct)
            logger.info(f"Authentification réussie pour {user}")
            return result
        except Exception as e:
            logger.error(f"Erreur d'authentification pour {user}: {e}")
            raise


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
        self.encoding = server_info.get('encoding', 'utf-8')
        self.client = None

    def connect(self):
        """Se connecter au serveur FTP."""
        try:
            # Créer une connexion FTP avec notre classe améliorée
            logger.info(f"Connexion à {self.host}:{self.port}...")
            
            # Créer le client
            self.client = EnhancedFTP(encoding=self.encoding)
            self.client.set_debuglevel(2)  # Niveau de débogage élevé
            self.client.timeout = self.timeout
            
            # Connexion
            self.client.connect(self.host, self.port, timeout=self.timeout)
            
            # Authentification
            self.client.login(self.username, self.password)
            
            # Mode passif
            if self.passive:
                logger.info("Utilisation du mode passif")
                self.client.set_pasv(True)
            else:
                logger.info("Utilisation du mode actif")
                self.client.set_pasv(False)
                
            logger.info("Connexion FTP établie avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur de connexion FTP: {str(e)}")
            self.close()
            return False
    
    def list_directory(self, path='/'):
        """Lister le contenu d'un répertoire."""
        if not self.client:
            if not self.connect():
                logger.error("Impossible de se connecter pour lister le répertoire")
                return []
                
        try:
            # Ajuster le chemin avec le chemin racine si nécessaire
            actual_path = self._adjust_path(path)
            logger.info(f"Listage du répertoire: {actual_path}")
            
            # Changer de répertoire
            try:
                self.client.cwd(actual_path)
                current_dir = self.client.pwd()
                logger.info(f"Répertoire courant: {current_dir}")
            except ftplib.error_perm as e:
                logger.error(f"Erreur de changement de répertoire: {e}")
                if "550" in str(e):  # La commande CWD a échoué
                    return []
            
            # Obtenir la liste des entrées du répertoire
            file_list = []
            try:
                # Utiliser MLSD si disponible (plus moderne et structuré)
                logger.debug("Tentative d'utilisation de MLSD...")
                entries = []
                self.client.mlsd(path=".", facts=["type", "size", "modify"])
                for name, facts in entries:
                    if name in ('.', '..'):
                        continue
                    
                    is_dir = facts["type"] == "dir"
                    size = int(facts.get("size", "0"))
                    
                    file_path = os.path.join(path, name) if path != '/' else '/' + name
                    
                    file_list.append({
                        'name': name,
                        'path': file_path,
                        'type': 'directory' if is_dir else 'file',
                        'size': size,
                        'size_human': self._format_size(size),
                        'is_directory': is_dir
                    })
            except:
                # Fallback sur LIST (plus traditionnel mais moins structuré)
                logger.debug("MLSD non disponible, utilisation de LIST...")
                lines = []
                self.client.retrlines('LIST', lines.append)
                
                for line in lines:
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
                        file_path = os.path.join(path, name) if path != '/' else '/' + name
                        
                        file_list.append({
                            'name': name,
                            'path': file_path,
                            'type': 'directory' if is_dir else 'file',
                            'size': size,
                            'size_human': self._format_size(size),
                            'is_directory': is_dir
                        })
                    except Exception as e:
                        logger.warning(f"Erreur lors du parsing d'une ligne: {e} (ligne: {line})")
            
            # Tri: répertoires d'abord, puis fichiers par ordre alphabétique
            return sorted(file_list, key=lambda x: (0 if x['is_directory'] else 1, x['name'].lower()))
                
        except Exception as e:
            logger.error(f"Erreur lors du listage du répertoire: {e}")
            
            # Tenter de se reconnecter et de réessayer
            try:
                logger.info("Tentative de reconnexion...")
                self.close()
                if self.connect():
                    actual_path = self._adjust_path(path)
                    self.client.cwd(actual_path)
                    
                    lines = []
                    self.client.retrlines('LIST', lines.append)
                    
                    file_list = []
                    for line in lines:
                        # Même logique de parsing que ci-dessus
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
                            file_path = os.path.join(path, name) if path != '/' else '/' + name
                            
                            file_list.append({
                                'name': name,
                                'path': file_path,
                                'type': 'directory' if is_dir else 'file',
                                'size': size,
                                'size_human': self._format_size(size),
                                'is_directory': is_dir
                            })
                        except Exception as e:
                            logger.warning(f"Erreur lors du parsing d'une ligne: {e}")
                    
                    return sorted(file_list, key=lambda x: (0 if x['is_directory'] else 1, x['name'].lower()))
                else:
                    logger.error("La reconnexion a échoué")
            except Exception as e:
                logger.error(f"Erreur lors de la tentative de reconnexion: {e}")
            
            return []
    
    def download_file(self, path):
        """Télécharger un fichier depuis le serveur FTP."""
        if not self.client:
            if not self.connect():
                raise Exception("Impossible de se connecter au serveur FTP")
                
        try:
            # Ajuster le chemin avec le chemin racine si nécessaire
            actual_path = self._adjust_path(path)
            logger.info(f"Téléchargement du fichier: {actual_path}")
            
            # Créer un buffer en mémoire pour recevoir le fichier
            buffer = io.BytesIO()
            
            # Télécharger le fichier
            self.client.retrbinary(f'RETR {actual_path}', buffer.write)
            
            # Rembobiner pour une utilisation ultérieure
            buffer.seek(0)
            
            return buffer
        except Exception as e:
            logger.error(f"Erreur lors du téléchargement du fichier: {e}")
            
            # Tentative de reconnexion et retry
            try:
                logger.info("Tentative de reconnexion pour téléchargement...")
                self.close()
                
                if self.connect():
                    actual_path = self._adjust_path(path)
                    buffer = io.BytesIO()
                    self.client.retrbinary(f'RETR {actual_path}', buffer.write)
                    buffer.seek(0)
                    return buffer
            except Exception as e:
                logger.error(f"Erreur lors de la tentative de reconnexion pour téléchargement: {e}")
            
            raise Exception(f"Échec du téléchargement: {e}")
    
    def _adjust_path(self, path):
        """Ajuster le chemin avec le chemin racine."""
        logger.debug(f"Ajustement du chemin: '{path}' avec racine: '{self.root_path}'")
        
        # Si le chemin racine n'est pas défini ou est /, retourner le chemin tel quel
        if not self.root_path or self.root_path == '/':
            logger.debug(f"Pas de chemin racine, utilisation de: {path}")
            return path
        
        # Nettoyer le chemin racine (s'assurer qu'il commence par /)
        root = self.root_path
        if not root.startswith('/'):
            root = '/' + root
        
        # Si le chemin demandé est /, retourner le chemin racine
        if path == '/':
            logger.debug(f"Chemin / demandé, utilisation du chemin racine: {root}")
            return root
        
        # Enlever le slash initial de path pour éviter le double slash
        path_no_slash = path.lstrip('/')
        
        # Construire le chemin complet
        if root.endswith('/'):
            full_path = root + path_no_slash
        else:
            full_path = root + '/' + path_no_slash
        
        logger.debug(f"Chemin ajusté: {full_path}")
        return full_path
    
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
                logger.info("Connexion FTP fermée")

# Fonction alternative utilisant la commande 'lftp'
def list_directory_with_lftp(server_info, path='/'):
    """Lister un répertoire en utilisant la commande lftp externe."""
    import subprocess
    
    host = server_info.get('host', '')
    port = server_info.get('port', 21)
    username = server_info.get('username', '')
    password = server_info.get('password', '')
    root_path = server_info.get('root_path', '/')
    
    # Ajuster le chemin
    if path == '/':
        target_path = root_path
    else:
        if root_path.endswith('/'):
            target_path = root_path + path.lstrip('/')
        else:
            target_path = root_path + '/' + path.lstrip('/')
    
    # Construire la commande lftp
    cmd = [
        'lftp', '-c',
        f'open -u {username},{password} {host}:{port}; ls -la {target_path}'
    ]
    
    logger.info(f"Exécution de lftp pour lister {target_path}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.error(f"Erreur lftp: {result.stderr}")
            return []
        
        # Parser la sortie
        files = []
        for line in result.stdout.splitlines():
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
                
                # Construire le chemin
                file_path = os.path.join(path, name) if path != '/' else '/' + name
                
                files.append({
                    'name': name,
                    'path': file_path,
                    'type': 'directory' if is_dir else 'file',
                    'size': size,
                    'is_directory': is_dir
                })
            except Exception as e:
                logger.warning(f"Erreur lors du parsing d'une ligne: {e}")
        
        return files
    except subprocess.TimeoutExpired:
        logger.error("Timeout lors de l'exécution de lftp")
        return []
    except Exception as e:
        logger.error(f"Erreur lors de l'utilisation de lftp: {e}")
        return []

def load_config():
    """Charger la configuration du fichier."""
    try:
        server_config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                server_config = json.load(f)
                logger.info(f"Configuration chargée: {len(server_config.get('ftp_servers', []))} serveurs")
        else:
            logger.warning(f"Fichier de configuration {CONFIG_FILE} introuvable")
            # Créer un fichier de configuration d'exemple
            server_config = {"ftp_servers": []}
            with open(CONFIG_FILE, 'w') as f:
                json.dump(server_config, f)
                
        return server_config
    except Exception as e:
        logger.error(f"Erreur de chargement de la configuration: {e}")
        return {"ftp_servers": []}

def get_server_info(server_id):
    """Obtenir les informations d'un serveur FTP par son ID."""
    config = load_config()
    servers = config.get('ftp_servers', [])
    
    if 0 <= server_id < len(servers):
        return servers[server_id]
    
    logger.error(f"Serveur {server_id} non trouvé")
    return None

# Routes de diagnostic 
@app.route('/diagnostic', methods=['GET'])
def run_diagnostic():
    """Exécuter un diagnostic complet du système."""
    import platform
    
    results = {
        'timestamp': time.time(),
        'system': {
            'python_version': sys.version,
            'platform': platform.platform(),
            'hostname': socket.gethostname(),
        },
        'configuration': {},
        'network': {},
        'servers': []
    }
    
    # Vérifier la configuration
    try:
        config = load_config()
        results['configuration'] = {
            'file_exists': os.path.exists(CONFIG_FILE),
            'server_count': len(config.get('ftp_servers', [])),
            'shares_dir_exists': os.path.exists(SHARES_DIR)
        }
    except Exception as e:
        results['configuration']['error'] = str(e)
    
    # Vérifier le réseau
    try:
        # Tester la connexion internet
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        status = s.connect_ex(('8.8.8.8', 53))
        s.close()
        results['network']['internet_access'] = status == 0
        
        # Tester la résolution DNS
        try:
            socket.gethostbyname('google.com')
            results['network']['dns_working'] = True
        except:
            results['network']['dns_working'] = False
    except Exception as e:
        results['network']['error'] = str(e)
    
    # Tester chaque serveur
    config = load_config()
    for i, server in enumerate(config.get('ftp_servers', [])):
        server_result = {
            'id': i,
            'name': server.get('name', f'Server {i}'),
            'host': server.get('host', ''),
            'port': server.get('port', 21)
        }
        
        # Tester la connexion TCP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            status = s.connect_ex((server.get('host', ''), server.get('port', 21)))
            s.close()
            server_result['tcp_connection'] = status == 0
        except Exception as e:
            server_result['tcp_error'] = str(e)
        
        results['servers'].append(server_result)
    
    return jsonify(results)

@app.route('/test_ftp/<int:server_id>', methods=['GET'])
def test_ftp(server_id):
    """Tester la connexion à un serveur FTP spécifique."""
    server_info = get_server_info(server_id)
    if not server_info:
        return jsonify({'error': 'Serveur non trouvé'}), 404
    
    logger.info(f"Test de connexion FTP à {server_info['name']} ({server_info['host']}:{server_info['port']})")
    
    result = {
        'server_id': server_id,
        'name': server_info.get('name', ''),
        'host': server_info.get('host', ''),
        'port': server_info.get('port', 21),
        'tests': {}
    }
    
    # Test 1: Connexion TCP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        start_time = time.time()
        status = s.connect_ex((server_info['host'], server_info['port']))
        connect_time = time.time() - start_time
        s.close()
        
        result['tests']['tcp_connection'] = {
            'success': status == 0,
            'time': round(connect_time, 3),
            'error': f"Erreur {status}" if status != 0 else None
        }
    except Exception as e:
        result['tests']['tcp_connection'] = {
            'success': False,
            'error': str(e)
        }
    
    # Test 2: Connexion FTP avec ftplib
    try:
        ftp = ftplib.FTP()
        ftp.set_debuglevel(1)
        start_time = time.time()
        ftp.connect(server_info['host'], server_info['port'], timeout=10)
        connect_time = time.time() - start_time
        
        welcome = ftp.getwelcome()
        
        login_start = time.time()
        ftp.login(server_info['username'], server_info['password'])
        login_time = time.time() - login_start
        
        current_dir = ftp.pwd()
        
        # Liste des fichiers
        files = []
        ftp.retrlines('LIST', files.append)
        
        ftp.quit()
        
        result['tests']['ftp_connection'] = {
            'success': True,
            'connect_time': round(connect_time, 3),
            'login_time': round(login_time, 3),
            'welcome': welcome,
            'current_dir': current_dir,
            'file_count': len(files)
        }
    except Exception as e:
        result['tests']['ftp_connection'] = {
            'success': False,
            'error': str(e)
        }
    
    # Test 3: Wrapper FTP personnalisé
    try:
        client = FTPClientWrapper(server_info)
        start_time = time.time()
        success = client.connect()
        connect_time = time.time() - start_time
        
        if success:
            list_start = time.time()
            files = client.list_directory()
            list_time = time.time() - list_start
            
            client.close()
            
            result['tests']['wrapper'] = {
                'success': True,
                'connect_time': round(connect_time, 3),
                'list_time': round(list_time, 3),
                'file_count': len(files)
            }
        else:
            result['tests']['wrapper'] = {
                'success': False,
                'error': 'Échec de connexion'
            }
    except Exception as e:
        result['tests']['wrapper'] = {
            'success': False,
            'error': str(e)
        }
    
    return jsonify(result)

# Routes API
@app.route('/servers', methods=['GET'])
def get_servers():
    """Obtenir la liste des serveurs FTP configurés."""
    try:
        config = load_config()
        
        # Ne pas renvoyer les mots de passe
        servers = []
        for i, server in enumerate(config.get('ftp_servers', [])):
            server_copy = server.copy()
            if 'password' in server_copy:
                server_copy['password'] = '********'
            server_copy['id'] = i
            servers.append(server_copy)
            
        return jsonify({'servers': servers})
    except Exception as e:
        logger.error(f"Erreur de récupération des serveurs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/browse/<int:server_id>', methods=['GET'])
def browse_server(server_id):
    """Parcourir un serveur FTP."""
    try:
        server_info = get_server_info(server_id)
        if not server_info:
            return jsonify({'error': 'Serveur non trouvé'}), 404
            
        path = request.args.get('path', '/')
        use_lftp = request.args.get('lftp', 'false').lower() == 'true'
        
        logger.info(f"Navigation sur le serveur {server_info['name']} ({server_info['host']}) chemin: {path}")
        logger.info(f"Mode lftp: {use_lftp}")
        
        if use_lftp:
            # Utiliser lftp comme alternative
            files = list_directory_with_lftp(server_info, path)
        else:
            # Utiliser le wrapper FTP standard
            client = FTPClientWrapper(server_info)
            
            # Tenter de se connecter avec des retry
            max_retries = 2
            connected = False
            
            for attempt in range(max_retries):
                try:
                    if client.connect():
                        connected = True
                        break
                    else:
                        logger.warning(f"Échec de connexion, tentative {attempt+1}/{max_retries}")
                        time.sleep(1)  # Petit délai entre les tentatives
                except Exception as e:
                    logger.error(f"Exception lors de la tentative {attempt+1}: {e}")
                    time.sleep(1)
            
            if not connected:
                return jsonify({
                    'error': 'Impossible de se connecter au serveur FTP après plusieurs tentatives'
                }), 500
            
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
        logger.error(f"Erreur de navigation: {e}")
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
        
        logger.info(f"Téléchargement du fichier {filename} depuis {server_info['name']}")
        
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
        logger.error(f"Erreur de téléchargement: {e}")
        return jsonify({'error': str(e)}), 500

# Gestion des partages
def load_shares():
    """Charger les partages."""
    shares_file = os.path.join(SHARES_DIR, "shares.json")
    if not os.path.exists(shares_file):
        return {}
    
    try:
        with open(shares_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erreur de chargement des partages: {e}")
        return {}

def save_shares(shares):
    """Sauvegarder les partages."""
    shares_file = os.path.join(SHARES_DIR, "shares.json")
    
    try:
        os.makedirs(SHARES_DIR, exist_ok=True)
        with open(shares_file, 'w') as f:
            json.dump(shares, f)
    except Exception as e:
        logger.error(f"Erreur de sauvegarde des partages: {e}")

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
            'server_name': server_info.get('name', ''),
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
        logger.error(f"Erreur de création de partage: {e}")
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
        logger.error(f"Erreur de listage des partages: {e}")
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
        
        server_id = share.get('server_id')
        path = share.get('path')
        filename = share.get('filename')
        
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
        logger.error(f"Erreur de téléchargement de fichier partagé: {e}")
        return jsonify({'error': str(e)}), 500

# Endpoint d'état API
@app.route('/health', methods=['GET'])
def health_check():
    """Vérifier la santé de l'API."""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'uptime': time.time() - startup_time
    })

# Nettoyage périodique
def clean_expired_shares():
    """Nettoyer les partages expirés."""
    while True:
        try:
            time.sleep(3600)  # Vérifier toutes les heures
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
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des partages: {e}")

# Démarrage de l'application
startup_time = time.time()

if __name__ == '__main__':
    logger.info("Initialisation de l'API FTP Browser...")
    
    # Créer les dossiers nécessaires
    os.makedirs(SHARES_DIR, exist_ok=True)
    
    # Démarrer le thread de nettoyage
    cleanup_thread = threading.Thread(target=clean_expired_shares)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    logger.info(f"Configuration chargée depuis {CONFIG_FILE}")
    config = load_config()
    server_count = len(config.get('ftp_servers', []))
    logger.info(f"{server_count} serveurs FTP configurés")
    
    try:
        # Ajouter un délai pour laisser le réseau s'initialiser
        time.sleep(2)
        logger.info("Serveur API FTP Browser démarré")
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du serveur: {e}")
        sys.exit(1)























