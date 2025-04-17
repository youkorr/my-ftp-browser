#!/usr/bin/env python3
"""Script de test de connexion FTP."""
import socket
import logging
import sys
import time

# Configuration du logger
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ftp-test")

class FTPTester:
    """Client FTP simplifié pour tester la connexion."""
    def __init__(self, host, port=21, timeout=30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.control_socket = None
        self.encoding = 'utf-8'
        
    def connect(self):
        """Se connecter au serveur FTP."""
        try:
            logger.info(f"Résolution DNS pour {self.host}...")
            try:
                host_info = socket.gethostbyname(self.host)
                logger.info(f"Résolution DNS: {self.host} -> {host_info}")
            except socket.gaierror as e:
                logger.error(f"Échec de la résolution DNS pour {self.host}: {e}")
                return False
            
            logger.info(f"Création du socket...")
            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            logger.info(f"Configuration du timeout à {self.timeout} secondes...")
            self.control_socket.settimeout(self.timeout)
            
            logger.info("Configuration des options de socket...")
            self.control_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.control_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 16384)
            
            logger.info(f"Tentative de connexion à {self.host}:{self.port}...")
            self.control_socket.connect((self.host, self.port))
            logger.info("Connexion établie!")
            
            logger.info("Attente du message de bienvenue...")
            buffer = b''
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                try:
                    chunk = self.control_socket.recv(1024)
                    if not chunk:
                        break
                    buffer += chunk
                    if b'\r\n' in buffer:
                        break
                except socket.timeout:
                    logger.warning("Timeout en attente du message de bienvenue")
                    break
            
            if not buffer:
                logger.error("Aucun message de bienvenue reçu")
                self.close()
                return False
                
            welcome_msg = buffer.decode(self.encoding).strip()
            logger.info(f"Message de bienvenue reçu: {welcome_msg}")
            
            if not welcome_msg.startswith('220'):
                logger.error(f"Message de bienvenue FTP non reconnu: {welcome_msg}")
                self.close()
                return False
            
            logger.info("Connexion FTP réussie!")
            return True
            
        except Exception as e:
            logger.error(f"Erreur de connexion FTP: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.close()
            return False
            
    def login(self, username, password):
        """S'authentifier au serveur FTP."""
        try:
            logger.info(f"Tentative d'authentification avec l'utilisateur: {username}")
            
            # Envoyer le nom d'utilisateur
            user_cmd = f"USER {username}\r\n"
            logger.debug(f"Envoi: {user_cmd.strip()}")
            self.control_socket.sendall(user_cmd.encode(self.encoding))
            
            logger.info("Attente de la réponse USER...")
            buffer = b''
            while True:
                chunk = self.control_socket.recv(1024)
                if not chunk:
                    break
                buffer += chunk
                if b'\r\n' in buffer:
                    break
            
            user_response = buffer.decode(self.encoding).strip()
            logger.info(f"Réponse USER: {user_response}")
            
            if not (user_response.startswith('230') or user_response.startswith('331')):
                logger.error(f"Réponse USER non reconnue: {user_response}")
                return False
                
            # Envoyer le mot de passe
            pass_cmd = f"PASS {password}\r\n"
            logger.debug("Envoi: PASS ********")
            self.control_socket.sendall(pass_cmd.encode(self.encoding))
            
            logger.info("Attente de la réponse PASS...")
            buffer = b''
            while True:
                chunk = self.control_socket.recv(1024)
                if not chunk:
                    break
                buffer += chunk
                if b'\r\n' in buffer:
                    break
            
            pass_response = buffer.decode(self.encoding).strip()
            logger.info(f"Réponse PASS: {pass_response}")
            
            if not pass_response.startswith('230'):
                logger.error(f"Authentification échouée: {pass_response}")
                return False
                
            logger.info("Authentification réussie!")
            
            # Mode binaire
            type_cmd = "TYPE I\r\n"
            logger.debug(f"Envoi: {type_cmd.strip()}")
            self.control_socket.sendall(type_cmd.encode(self.encoding))
            
            logger.info("Attente de la réponse TYPE I...")
            buffer = b''
            while True:
                chunk = self.control_socket.recv(1024)
                if not chunk:
                    break
                buffer += chunk
                if b'\r\n' in buffer:
                    break
            
            type_response = buffer.decode(self.encoding).strip()
            logger.info(f"Réponse TYPE I: {type_response}")
            
            if not type_response.startswith('200'):
                logger.warning(f"Échec de configuration du mode binaire: {type_response}")
                
            return True
            
        except Exception as e:
            logger.error(f"Erreur d'authentification FTP: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
    def close(self):
        """Fermer la connexion."""
        try:
            if self.control_socket:
                logger.info("Fermeture de la connexion FTP...")
                try:
                    self.control_socket.sendall(b"QUIT\r\n")
                    self.control_socket.recv(1024)  # Récupérer la réponse
                except Exception:
                    pass
                finally:
                    self.control_socket.close()
                    self.control_socket = None
                    logger.info("Connexion fermée")
        except Exception as e:
            logger.error(f"Erreur de fermeture de connexion FTP: {e}")

def main():
    """Fonction principale."""
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} host username password [port]")
        sys.exit(1)
        
    host = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 21
    
    logger.info(f"Test de connexion FTP vers {host}:{port}")
    
    tester = FTPTester(host, port)
    
    if tester.connect():
        logger.info("Connexion réussie, tentative d'authentification...")
        if tester.login(username, password):
            logger.info("Test complet réussi!")
        else:
            logger.error("Test échoué: Authentification impossible")
    else:
        logger.error("Test échoué: Connexion impossible")
        
    tester.close()

if __name__ == "__main__":
    main()


