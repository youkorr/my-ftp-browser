from flask import Flask, request, jsonify
import ftputil
import os
from dotenv import load_dotenv
import json
from datetime import datetime

app = Flask(__name__)

# Charger la configuration
load_dotenv('/data/options.json')

@app.route('/api/list')
def list_files():
    path = request.args.get('path', '/')
    try:
        with ftputil.FTPHost(
            os.getenv('ftp_host'), 
            os.getenv('ftp_user'), 
            os.getenv('ftp_pass')
        ) as host:
            items = []
            for name in host.listdir(path):
                full_path = host.path.join(path, name)
                if host.path.isfile(full_path):
                    items.append({
                        'name': name,
                        'path': full_path,
                        'size': host.path.getsize(full_path),
                        'type': 'file',
                        'modified': datetime.fromtimestamp(
                            host.path.getmtime(full_path)
                        ).isoformat()
                    })
                else:
                    items.append({
                        'name': name,
                        'path': full_path,
                        'size': 0,
                        'type': 'directory',
                        'modified': datetime.fromtimestamp(
                            host.path.getmtime(full_path)
                        ).isoformat()
                    })
            return jsonify(items)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download')
def download_file():
    path = request.args.get('path')
    # Implémentation du téléchargement
    pass

@app.route('/api/upload', methods=['POST'])
def upload_file():
    # Implémentation de l'upload
    pass

@app.route('/api/share', methods=['POST'])
def share_file():
    # Implémentation du partage
    pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
