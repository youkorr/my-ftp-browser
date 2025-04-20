#!/usr/bin/env python3
import os
import json
import ftplib
import ssl
from flask import Flask, request, jsonify, send_from_directory

# Créer l'application Flask
app = Flask(__name__, static_folder='../js')

# Récupérer les informations de configuration depuis les variables d'environnement
FTP_USER = os.environ.get('FTP_USER', '')
FTP_PASS = os.environ.get('FTP_PASS', '')
FTP_PORT = int(os.environ.get('FTP_PORT', 21))
SSL_ENABLED = os.environ.get('SSL', 'false').lower() == 'true'
PASSIVE_MODE = os.environ.get('PASSIVE_MODE', 'true').lower() == 'true'
ALLOW_UPLOAD = os.environ.get('ALLOW_UPLOAD', 'true').lower() == 'true'
ALLOW_DELETE = os.environ.get('ALLOW_DELETE', 'true').lower() == 'true'

# Servir les fichiers statiques de l'application
@app.route('/')
def index():
    return send_from_directory('../', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('../', path)

# Endpoint pour lister les fichiers
@app.route('/api/list', methods=['POST'])
def list_files():
    data = request.json
    path = data.get('path', '/')
    
    try:
        # Créer une connexion FTP
        if SSL_ENABLED:
            ftp = ftplib.FTP_TLS()
            ftp.connect('localhost', FTP_PORT)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.prot_p()
        else:
            ftp = ftplib.FTP()
            ftp.connect('localhost', FTP_PORT)
            ftp.login(FTP_USER, FTP_PASS)
        
        # Configurer le mode passif si nécessaire
        if PASSIVE_MODE:
            ftp.set_pasv(True)
        
        # Changer de répertoire
        ftp.cwd(path)
        
        # Lister les fichiers
        files = []
        directories = []
        
        def process_line(line):
            parts = line.split()
            if len(parts) >= 9:
                name = ' '.join(parts[8:])
                size = parts[4]
                date = ' '.join(parts[5:8])
                is_dir = parts[0].startswith('d')
                
                if is_dir:
                    directories.append({
                        'name': name,
                        'isDirectory': True,
                        'size': size,
                        'date': date
                    })
                else:
                    files.append({
                        'name': name,
                        'isDirectory': False,
                        'size': size,
                        'date': date
                    })
        
        ftp.retrlines('LIST', process_line)
        ftp.quit()
        
        # Trier les répertoires puis les fichiers par nom
        directories.sort(key=lambda x: x['name'])
        files.sort(key=lambda x: x['name'])
        
        return jsonify({
            'success': True,
            'path': path,
            'items': directories + files
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Endpoint pour télécharger un fichier
@app.route('/api/download', methods=['POST'])
def download_file():
    data = request.json
    path = data.get('path', '')
    filename = data.get('filename', '')
    
    if not path or not filename:
        return jsonify({
            'success': False,
            'error': 'Chemin ou nom de fichier manquant'
        }), 400
    
    try:
        # Créer une connexion FTP
        if SSL_ENABLED:
            ftp = ftplib.FTP_TLS()
            ftp.connect('localhost', FTP_PORT)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.prot_p()
        else:
            ftp = ftplib.FTP()
            ftp.connect('localhost', FTP_PORT)
            ftp.login(FTP_USER, FTP_PASS)
        
        # Configurer le mode passif si nécessaire
        if PASSIVE_MODE:
            ftp.set_pasv(True)
        
        # Changer de répertoire
        ftp.cwd(path)
        
        # Créer le répertoire temporaire si nécessaire
        temp_dir = '/tmp/ftp-downloads'
        os.makedirs(temp_dir, exist_ok=True)
        
        # Télécharger le fichier
        local_file = os.path.join(temp_dir, filename)
        with open(local_file, 'wb') as f:
            ftp.retrbinary(f'RETR {filename}', f.write)
        
        ftp.quit()
        
        # Renvoyer le fichier
        return send_from_directory(temp_dir, filename, as_attachment=True)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Endpoint pour uploader un fichier
@app.route('/api/upload', methods=['POST'])
def upload_file():
    if not ALLOW_UPLOAD:
        return jsonify({
            'success': False,
            'error': 'Upload non autorisé'
        }), 403
    
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'Aucun fichier trouvé'
        }), 400
    
    path = request.form.get('path', '/')
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'Nom de fichier vide'
        }), 400
    
    try:
        # Sauvegarder temporairement le fichier
        temp_dir = '/tmp/ftp-uploads'
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, file.filename)
        file.save(temp_file)
        
        # Créer une connexion FTP
        if SSL_ENABLED:
            ftp = ftplib.FTP_TLS()
            ftp.connect('localhost', FTP_PORT)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.prot_p()
        else:
            ftp = ftplib.FTP()
            ftp.connect('localhost', FTP_PORT)
            ftp.login(FTP_USER, FTP_PASS)
        
        # Configurer le mode passif si nécessaire
        if PASSIVE_MODE:
            ftp.set_pasv(True)
        
        # Changer de répertoire
        ftp.cwd(path)
        
        # Uploader le fichier
        with open(temp_file, 'rb') as f:
            ftp.storbinary(f'STOR {file.filename}', f)
        
        ftp.quit()
        
        # Supprimer le fichier temporaire
        os.remove(temp_file)
        
        return jsonify({
            'success': True,
            'message': f'Fichier {file.filename} uploadé avec succès'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Endpoint pour supprimer un fichier ou un répertoire
@app.route('/api/delete', methods=['POST'])
def delete_item():
    if not ALLOW_DELETE:
        return jsonify({
            'success': False,
            'error': 'Suppression non autorisée'
        }), 403
    
    data = request.json
    path = data.get('path', '/')
    name = data.get('name', '')
    is_directory = data.get('isDirectory', False)
    
    if not name:
        return jsonify({
            'success': False,
            'error': 'Nom manquant'
        }), 400
    
    try:
        # Créer une connexion FTP
        if SSL_ENABLED:
            ftp = ftplib.FTP_TLS()
            ftp.connect('localhost', FTP_PORT)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.prot_p()
        else:
            ftp = ftplib.FTP()
            ftp.connect('localhost', FTP_PORT)
            ftp.login(FTP_USER, FTP_PASS)
        
        # Configurer le mode passif si nécessaire
        if PASSIVE_MODE:
            ftp.set_pasv(True)
        
        # Changer de répertoire
        ftp.cwd(path)
        
        # Supprimer le fichier ou le répertoire
        if is_directory:
            ftp.rmd(name)
        else:
            ftp.delete(name)
        
        ftp.quit()
        
        return jsonify({
            'success': True,
            'message': f'{"Répertoire" if is_directory else "Fichier"} {name} supprimé avec succès'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Endpoint pour créer un répertoire
@app.route('/api/mkdir', methods=['POST'])
def create_directory():
    if not ALLOW_UPLOAD:
        return jsonify({
            'success': False,
            'error': 'Création de répertoire non autorisée'
        }), 403
    
    data = request.json
    path = data.get('path', '/')
    name = data.get('name', '')
    
    if not name:
        return jsonify({
            'success': False,
            'error': 'Nom manquant'
        }), 400
    
    try:
        # Créer une connexion FTP
        if SSL_ENABLED:
            ftp = ftplib.FTP_TLS()
            ftp.connect('localhost', FTP_PORT)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.prot_p()
        else:
            ftp = ftplib.FTP()
            ftp.connect('localhost', FTP_PORT)
            ftp.login(FTP_USER, FTP_PASS)
        
        # Configurer le mode passif si nécessaire
        if PASSIVE_MODE:
            ftp.set_pasv(True)
        
        # Changer de répertoire
        ftp.cwd(path)
        
        # Créer le répertoire
        ftp.mkd(name)
        
        ftp.quit()
        
        return jsonify({
            'success': True,
            'message': f'Répertoire {name} créé avec succès'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Endpoint pour renommer un fichier ou un répertoire
@app.route('/api/rename', methods=['POST'])
def rename_item():
    if not ALLOW_UPLOAD:
        return jsonify({
            'success': False,
            'error': 'Renommage non autorisé'
        }), 403
    
    data = request.json
    path = data.get('path', '/')
    old_name = data.get('oldName', '')
    new_name = data.get('newName', '')
    
    if not old_name or not new_name:
        return jsonify({
            'success': False,
            'error': 'Nom ancien ou nouveau manquant'
        }), 400
    
    try:
        # Créer une connexion FTP
        if SSL_ENABLED:
            ftp = ftplib.FTP_TLS()
            ftp.connect('localhost', FTP_PORT)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.prot_p()
        else:
            ftp = ftplib.FTP()
            ftp.connect('localhost', FTP_PORT)
            ftp.login(FTP_USER, FTP_PASS)
        
        # Configurer le mode passif si nécessaire
        if PASSIVE_MODE:
            ftp.set_pasv(True)
        
        # Changer de répertoire
        ftp.cwd(path)
        
        # Renommer le fichier ou le répertoire
        ftp.rename(old_name, new_name)
        
        ftp.quit()
        
        return jsonify({
            'success': True,
            'message': f'Élément renommé de {old_name} à {new_name} avec succès'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Lancer l'application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)





















