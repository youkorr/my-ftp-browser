#!/usr/bin/env python3
"""Script de test pour la connexion FTP."""
import socket
import ssl
import re
import sys
import time
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ftp-test')

class FTPTester:
    def __init__(self, host, port=21, username='', password='', timeout=30, use_ssl=False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.control_socket = None
        self.encoding = 'utf-8'
        self.use_ssl = use_ssl
        self.debug = True
        
    def connect_and_login(self):
        """Test de connexion et d'authentification."""
        try:
            logger.info(f"Tentative de connexion à {self.host}:{self.port}")
            
            # Connexion
            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.control_socket.settimeout(self.timeout)
            
            # Support SSL si nécessaire
            if self.use_ssl:
                logger.info("Utilisation de SSL/TLS")
                context = ssl.create_default_context()
                self.control_socket = context.wrap_socket(
                    self.control_socket,
                    server_hostname=self.host
                )
            
            self.control_socket.connect((self.host, self.port))
            
            # Lire le message de bienvenue
            response = self._read_response()
            logger.debug(f"Message de bienvenue: {response}")
            
            if not response.startswith('220'):
                logger.error(f"Message de bienvenue FTP non reçu: {response}")
                return False
                
            # Authentification
            logger.info(f"Envoi du nom d'utilisateur: {self.username}")
            self._send_command(f"USER {self.username}")
            response = self._read_response()
            logger.debug(f"Réponse USER: {response}")
            
            if not (response.startswith('230') or response.startswith('331')):
                logger.error(f"Échec d'authentification (nom d'utilisateur): {response}")
                return False
            
            if response.startswith('331'):
                logger.info("Envoi mot de passe")
                self._send_command(f"PASS {self.password}")
                response = self._read_response()
                logger.debug(f"Réponse PASS: {response}")
                
                if not response.startswith('230'):
                    logger.error(f"Échec d'authentification (mot de passe): {response}")
                    return False
            
            # Mode binaire
            logger.info("Configuration du mode binaire")
            self._send_command("TYPE I")
            response = self._read_response()
            logger.debug(f"Réponse TYPE I: {response}")
            
            if not response.startswith('200'):
                logger.error(f"Échec de configuration du mode binaire: {response}")
                return False
                
            logger.info("Test de mode passif")
            data_socket, addr = self._enter_passive_mode()
            if not data_socket:
                logger.error("Échec du mode passif")
                return False
            
            logger.info(f"Connexion en mode passif réussie à {addr}")
            data_socket.close()
            
            logger.info("Test réussi!")
            return True
            
        except Exception as e:
            logger.error(f"Erreur de test: {e}")
            return False
        finally:
            self.close()
            
    def _send_command(self, command):
        """Envoyer une commande au serveur FTP."""
        if not self.control_socket:
            raise ConnectionError("Non connecté au serveur FTP")
            
        cmd_bytes = (command + '\r\n').encode(self.encoding)
        logger.debug(f"Envoi: {command}")
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
        
    def _enter_passive_mode(self):
        """Passer en mode passif et retourner le socket de données."""
        try:
            self._send_command("PASV")
            response = self._read_response()
            logger.debug(f"Réponse PASV: {response}")
            
            if not response.startswith('227'):
                logger.error(f"Échec du mode passif: {response}")
                return None, None
            
            # Parser la réponse pour extraire l'IP et le port
            match = re.search(r'(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', response)
            if not match:
                logger.error(f"Erreur de parsing de la réponse PASV: {response}")
                return None, None
                
            ip_parts = match.groups()[:4]
            port_parts = match.groups()[4:]
            
            # Méthode 1: utiliser l'IP renvoyée par le serveur
            ip = '.'.join(ip_parts)
            port = (int(port_parts[0]) << 8) + int(port_parts[1])
            logger.debug(f"IP extraite: {ip}, Port: {port}")
            
            try:
                # Essayer d'abord avec l'IP renvoyée par le serveur
                logger.debug(f"Test de connexion avec l'IP renvoyée: {ip}:{port}")
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(self.timeout)
                s.connect((ip, port))
                return s, (ip, port)
            except Exception as e:
                logger.warning(f"Échec de connexion avec l'IP renvoyée: {e}")
                logger.info("Tentative avec l'IP du serveur d'origine...")
                
                # Méthode 2: utiliser l'IP du serveur d'origine
                ip = self.host
                logger.debug(f"Tentative avec l'IP du serveur: {ip}:{port}")
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(self.timeout)
                s.connect((ip, port))
                return s, (ip, port)
            
        except Exception as e:
            logger.error(f"Erreur de passage en mode passif: {e}")
            return None, None
        
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
            logger.error(f"Erreur de fermeture de connexion FTP: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test de connexion FTP')
    parser.add_argument('host', help='Adresse du serveur FTP')
    parser.add_argument('port', type=int, default=21, help='Port FTP (défaut: 21)')
    parser.add_argument('username', help='Nom d\'utilisateur')
    parser.add_argument('password', help='Mot de passe')
    parser.add_argument('--ssl', action='store_true', help='Utiliser SSL/TLS')
    parser.add_argument('--timeout', type=int, default=30, help='Timeout en secondes (défaut: 30)')
    
    args = parser.parse_args()
    
    tester = FTPTester(args.host, args.port, args.username, args.password, args.timeout, args.ssl)
    if tester.connect_and_login():
        print("Connexion réussie!")
        sys.exit(0)
    else:
        print("Échec de connexion.")
        sys.exit(1)










