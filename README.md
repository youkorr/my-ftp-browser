# FTP Browser & Media Server pour Home Assistant

Ce add-on vous permet d'accéder facilement à vos serveurs FTP directement depuis Home Assistant, de partager des fichiers, et de gérer les médias.

## Fonctionnalités

- **Interface utilisateur intuitive**: Parcourez vos fichiers FTP avec une interface web moderne
- **Multiples serveurs**: Configurez et accédez à plusieurs serveurs FTP
- **Partage de fichiers**: Créez des liens de partage temporaires pour n'importe quel fichier
- **Planification avancée**: Définissez des horaires précis pour l'accès aux fichiers partagés
- **Téléchargement direct**: Téléchargez facilement les fichiers depuis l'interface
- **Intégration Home Assistant**: Utilisez les fichiers partagés dans vos automatisations

## Installation

1. Ajoutez ce dépôt à vos dépôts add-on dans Home Assistant
2. Installez l'add-on "FTP Browser & Media Server"
3. Configurez vos serveurs FTP dans les options de l'add-on
4. Démarrez l'add-on
5. Accédez à l'interface utilisateur depuis le panneau latéral

## Configuration

Exemple de configuration minimale:

ftp_servers:
  - name: Mon ESP32
    host: 192.168.1.123
    port: 21
    username: admin
    password: password
    root_path: /sdcard
    use_ssl: false
share_settings:
  default_duration: 24
  max_duration: 168
  show_share_link: true
log_level: info
