document.addEventListener('DOMContentLoaded', function() {
    // État de l'application
    const appState = {
        currentServer: null,
        currentPath: '/',
        servers: [],
        shareData: null
    };

    // Éléments DOM
    const elements = {
        serverList: document.getElementById('server-list'),
        currentLocation: document.getElementById('current-location'),
        pathBreadcrumb: document.getElementById('path-breadcrumb'),
        fileBrowserContent: document.getElementById('file-browser-content'),
        sharedLinks: document.getElementById('shared-links'),
        shareModal: new bootstrap.Modal(document.getElementById('shareModal')),
        shareDuration: document.getElementById('share-duration'),
        advancedScheduling: document.getElementById('advanced-scheduling'),
        shareResult: document.getElementById('share-result'),
        shareLink: document.getElementById('share-link'),
        shareExpiry: document.getElementById('share-expiry'),
        createShareBtn: document.getElementById('create-share-btn'),
        copyLinkBtn: document.getElementById('copy-link-btn')
    };

    // Chargement initial
    loadServers();
    loadSharedLinks();

    // Gestionnaires d'événements
    elements.shareDuration.addEventListener('change', function() {
        if (this.value === '-1') {
            elements.advancedScheduling.style.display = 'block';
        } else {
            elements.advancedScheduling.style.display = 'none';
        }
    });

    elements.createShareBtn.addEventListener('click', createShareLink);
    elements.copyLinkBtn.addEventListener('click', copyShareLink);

    // Initialiser la date d'expiration par défaut à un mois plus tard
    const defaultExpiryDate = new Date();
    defaultExpiryDate.setMonth(defaultExpiryDate.getMonth() + 1);
    document.getElementById('expiry-date').valueAsDate = defaultExpiryDate;

    // Fonctions
    function loadServers() {
        fetch('/api/servers')
            .then(response => response.json())
            .then(data => {
                appState.servers = data.servers;
                renderServerList();
            })
            .catch(error => {
                console.error('Erreur de chargement des serveurs:', error);
                elements.serverList.innerHTML = '<li class="list-group-item text-danger">Erreur de chargement des serveurs</li>';
            });
    }

    function renderServerList() {
        if (appState.servers.length === 0) {
            elements.serverList.innerHTML = '<li class="list-group-item">Aucun serveur configuré</li>';
            return;
        }

        const html = appState.servers.map((server, index) => {
            const activeClass = appState.currentServer === index ? 'active' : '';
            return `
                <li class="list-group-item ${activeClass} server-item" data-server-id="${index}">
                    <i class="bi bi-hdd-network me-2"></i> ${server.name}
                </li>
            `;
        }).join('');

        elements.serverList.innerHTML = html;

        // Ajouter des écouteurs d'événements aux éléments de la liste
        document.querySelectorAll('.server-item').forEach(item => {
            item.addEventListener('click', function() {
                const serverId = parseInt(this.dataset.serverId);
                selectServer(serverId);
            });
        });
    }

    function selectServer(serverId) {
        appState.currentServer = serverId;
        appState.currentPath = '/';
        renderServerList();
        browseServer(serverId, '/');
    }

    function browseServer(serverId, path) {
        elements.fileBrowserContent.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border" role="status">
                    <span class="visually-hidden">Chargement...</span>
                </div>
                <p class="mt-3">Chargement des fichiers...</p>
            </div>
        `;

        fetch(`/api/browse/${serverId}?path=${encodeURIComponent(path)}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                
                appState.currentPath = path;
                renderFileBrowser(data);
                updateBreadcrumb(path, data.server_name);
            })
            .catch(error => {
                console.error('Erreur de navigation:', error);
                elements.fileBrowserContent.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Erreur: ${error.message || 'Impossible de charger les fichiers'}
                    </div>
                `;
            });
    }

    function renderFileBrowser(data) {
        const files = data.files;

        if (files.length === 0) {
            elements.fileBrowserContent.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-folder2-open display-1 text-muted"></i>
                    <h3 class="mt-3">Dossier vide</h3>
                    <p class="text-muted">Ce dossier ne contient aucun fichier</p>
                </div>
            `;
            return;
        }

        const html = files.map(file => {
            let icon = 'bi-file-earmark';
            
            if (file.is_directory) {
                icon = 'bi-folder-fill';
            } else {
                // Déterminer l'icône en fonction de l'extension
                const ext = file.name.split('.').pop().toLowerCase();
                if (['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext)) {
                    icon = 'bi-file-earmark-image';
                } else if (['mp3', 'wav', 'ogg', 'flac'].includes(ext)) {
                    icon = 'bi-file-earmark-music';
                } else if (['mp4', 'avi', 'mkv', 'mov', 'webm'].includes(ext)) {
                    icon = 'bi-file-earmark-play';
                } else if (['txt', 'log', 'md', 'json'].includes(ext)) {
                    icon = 'bi-file-earmark-text';
                } else if (ext === 'pdf') {
                    icon = 'bi-file-earmark-pdf';
                }
            }

            const actions = file.is_directory 
                ? ''
                : `
                    <div class="file-actions">
                        <button class="btn btn-sm btn-primary download-btn" data-path="${file.path}">
                            <i class="bi bi-download"></i>
                        </button>
                        <button class="btn btn-sm btn-info share-btn" data-path="${file.path}" data-name="${file.name}">
                            <i class="bi bi-share"></i>
                        </button>
                    </div>
                `;

            return `
                <div class="file-item" data-path="${file.path}" data-is-dir="${file.is_directory}">
                    <i class="bi ${icon}"></i>
                    <div class="file-name">${file.name}</div>
                    <div class="file-meta">${file.size_human}</div>
                    ${actions}
                </div>
            `;
        }).join('');

        elements.fileBrowserContent.innerHTML = html;

        // Ajouter des écouteurs d'événements
        document.querySelectorAll('.file-item').forEach(item => {
            item.addEventListener('click', function(e) {
                // Si le clic est sur un bouton, ne pas naviguer
                if (e.target.closest('.download-btn') || e.target.closest('.share-btn')) {
                    return;
                }

                const path = this.dataset.path;
                const isDir = this.dataset.isDir === 'true';
                
                if (isDir) {
                    browseServer(appState.currentServer, path);
                }
            });
        });

        document.querySelectorAll('.download-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const path = this.dataset.path;
                downloadFile(appState.currentServer, path);
            });
        });

        document.querySelectorAll('.share-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const path = this.dataset.path;
                const name = this.dataset.name;
                openShareModal(appState.currentServer, path, name);
            });
        });
    }

    function updateBreadcrumb(path, serverName) {
        elements.currentLocation.textContent = serverName || 'Explorateur de fichiers';
        
        // Construire le fil d'Ariane
        const parts = path.split('/').filter(part => part !== '');
        let html = `<li class="breadcrumb-item"><a href="#" data-path="/">Racine</a></li>`;
        
        let currentPath = '';
        parts.forEach((part, index) => {
            currentPath += '/' + part;
            html += `
                <li class="breadcrumb-item ${index === parts.length - 1 ? 'active' : ''}">
                    ${index === parts.length - 1 ? part : `<a href="#" data-path="${currentPath}">${part}</a>`}
                </li>
            `;
        });
        
        elements.pathBreadcrumb.innerHTML = html;
        
        // Ajouter des écouteurs d'événements aux liens du fil d'Ariane
        document.querySelectorAll('#path-breadcrumb a').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const path = this.dataset.path;
                browseServer(appState.currentServer, path);
            });
        });
    }

    function downloadFile(serverId, path) {
        window.location.href = `/api/download/${serverId}?path=${encodeURIComponent(path)}`;
    }

    function openShareModal(serverId, path, filename) {
        // Réinitialiser le modal
        elements.shareResult.style.display = 'none';
        elements.createShareBtn.style.display = 'block';
        elements.shareDuration.value = '24'; // Par défaut 24 heures
        elements.advancedScheduling.style.display = 'none';
        
        // Définir le titre du modal
        document.getElementById('shareModalLabel').textContent = `Partager: ${filename}`;
        
        // Stocker les données de partage
        appState.shareData = {
            serverId: serverId,
            path: path,
            filename: filename
        };
        
        // Afficher le modal
        elements.shareModal.show();
    }

    function createShareLink() {
        if (!appState.shareData) return;
        
        elements.createShareBtn.disabled = true;
        elements.createShareBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Création...';
        
        const duration = elements.shareDuration.value;
        let requestData = {
            server_id: appState.shareData.serverId,
            path: appState.shareData.path
        };
        
        // Options de base ou avancées
        if (duration === '-1') {
            // Planification avancée
            const days = Array.from(document.querySelectorAll('.day-check:checked')).map(cb => parseInt(cb.value));
            const startTime = document.getElementById('start-time').value;
            const endTime = document.getElementById('end-time').value;
            const expiryDate = document.getElementById('expiry-date').value;
            
            const startHour = parseInt(startTime.split(':')[0]);
            const startMinute = parseInt(startTime.split(':')[1]);
            const endHour = parseInt(endTime.split(':')[0]);
            const endMinute = parseInt(endTime.split(':')[1]);
            
            const expiry = new Date(expiryDate);
            expiry.setHours(23, 59, 59);
            
            requestData.schedule = {
                days: days,
                start_time: (new Date()).setHours(startHour, startMinute, 0) / 1000,
                end_time: (new Date()).setHours(endHour, endMinute, 0) / 1000,
                expiry: expiry.getTime() / 1000
            };
            
            fetch('/api/schedule', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            })
            .then(response => response.json())
            .then(handleShareResponse)
            .catch(handleShareError);
            
        } else {
            // Partage simple
            requestData.duration = parseInt(duration);
            
            fetch('/api/share', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            })
            .then(response => response.json())
            .then(handleShareResponse)
            .catch(handleShareError);
        }
    }
    
    function handleShareResponse(data) {
        elements.createShareBtn.disabled = false;
        elements.createShareBtn.innerHTML = 'Créer un lien';
        elements.createShareBtn.style.display = 'none';
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Afficher le résultat
        elements.shareResult.style.display = 'block';
        elements.shareExpiry.textContent = data.expiry_human;
        
        // Construire l'URL complète
        const baseUrl = window.location.origin;
        const shareUrl = `${baseUrl}${data.url}`;
        elements.shareLink.value = shareUrl;
        
        // Ajouter le partage à la liste
        loadSharedLinks();
    }
    
    function handleShareError(error) {
        elements.createShareBtn.disabled = false;
        elements.createShareBtn.innerHTML = 'Créer un lien';
        
        alert(`Erreur: ${error.message || 'Impossible de créer le lien de partage'}`);
        console.error('Erreur de partage:', error);
    }

    function copyShareLink() {
        elements.shareLink.select();
        document.execCommand('copy');
        
        // Animation de confirmation
        const originalText = elements.copyLinkBtn.textContent;
        elements.copyLinkBtn.innerHTML = '<i class="bi bi-check"></i> Copié!';
        elements.copyLinkBtn.classList.add('btn-success');
        elements.copyLinkBtn.classList.remove('btn-outline-secondary');
        
        setTimeout(() => {
            elements.copyLinkBtn.textContent = originalText;
            elements.copyLinkBtn.classList.remove('btn-success');
            elements.copyLinkBtn.classList.add('btn-outline-secondary');
        }, 2000);
    }

    function loadSharedLinks() {
        fetch('/api/shares')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                
                if (Object.keys(data.shares).length === 0) {
                    elements.sharedLinks.innerHTML = '<li class="list-group-item text-center">Aucun lien partagé</li>';
                    return;
                }
                
                const now = Date.now() / 1000;
                let html = '';
                
                // Convertir l'objet en tableau pour le tri
                const sharesArray = Object.entries(data.shares).map(([token, share]) => ({
                    token,
                    ...share
                }));
                
                // Trier par date de création (le plus récent en premier)
                sharesArray.sort((a, b) => b.created - a.created);
                
                for (const share of sharesArray) {
                    const expiryDate = new Date(share.expiry * 1000);
                    const remainingTime = getTimeRemaining(now, share.expiry);
                    const progressPercent = 100 - (remainingTime.percent || 0);
                    
                    html += `
                        <li class="list-group-item share-item">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <div class="share-title">${share.filename}</div>
                                    <div class="share-meta">
                                        ${share.server_name} · Expire ${remainingTime.text}
                                    </div>
                                </div>
                                <div>
                                    <button class="btn btn-sm btn-danger delete-share-btn" data-token="${share.token}">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="progress mt-2" style="height: 3px;">
                                <div class="progress-bar" role="progressbar" style="width: ${progressPercent}%;" 
                                    aria-valuenow="${progressPercent}" aria-valuemin="0" aria-valuemax="100"></div>
                            </div>
                            <div class="share-actions">
                                <button class="btn btn-sm btn-primary copy-share-btn" 
                                    data-url="${window.location.origin}/api/download/${share.token}">
                                    <i class="bi bi-clipboard"></i> Copier le lien
                                </button>
                                <a href="/api/download/${share.token}" class="btn btn-sm btn-success" target="_blank">
                                    <i class="bi bi-download"></i> Télécharger
                                </a>
                            </div>
                        </li>
                    `;
                }
                
                elements.sharedLinks.innerHTML = html;
                
                // Ajouter les écouteurs d'événements
                document.querySelectorAll('.delete-share-btn').forEach(btn => {
                    btn.addEventListener('click', function() {
                        deleteShare(this.dataset.token);
                    });
                });
                
                document.querySelectorAll('.copy-share-btn').forEach(btn => {
                    btn.addEventListener('click', function() {
                        const url = this.dataset.url;
                        navigator.clipboard.writeText(url).then(() => {
                            const originalHTML = this.innerHTML;
                            this.innerHTML = '<i class="bi bi-check"></i> Copié!';
                            
                            setTimeout(() => {
                                this.innerHTML = originalHTML;
                            }, 2000);
                        });
                    });
                });
            })
            .catch(error => {
                console.error('Erreur de chargement des partages:', error);
                elements.sharedLinks.innerHTML = `
                    <li class="list-group-item text-danger">
                        Erreur: ${error.message || 'Impossible de charger les partages'}
                    </li>
                `;
            });
    }

    function deleteShare(token) {
        if (!confirm('Voulez-vous vraiment supprimer ce lien de partage?')) {
            return;
        }
        
        fetch(`/api/shares/${token}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            loadSharedLinks();
        })
        .catch(error => {
            console.error('Erreur de suppression de partage:', error);
            alert(`Erreur: ${error.message || 'Impossible de supprimer le partage'}`);
        });
    }

    function getTimeRemaining(now, expiryTime) {
        const totalSeconds = expiryTime - now;
        
        if (totalSeconds <= 0) {
            return { text: 'expiré', percent: 100 };
        }
        
        // Calculer le pourcentage du temps écoulé (supposons 7 jours max)
        const maxDuration = 7 * 24 * 60 * 60; // 7 jours en secondes
        const percent = Math.min(100, (totalSeconds / maxDuration) * 100);
        
        // Formater le texte
        if (totalSeconds < 60) {
            return { text: 'dans moins d\'une minute', percent };
        } else if (totalSeconds < 3600) {
            const minutes = Math.floor(totalSeconds / 60);
            return { text: `dans ${minutes} minute${minutes > 1 ? 's' : ''}`, percent };
        } else if (totalSeconds < 86400) {
            const hours = Math.floor(totalSeconds / 3600);
            return { text: `dans ${hours} heure${hours > 1 ? 's' : ''}`, percent };
        } else {
            const days = Math.floor(totalSeconds / 86400);
            return { text: `dans ${days} jour${days > 1 ? 's' : ''}`, percent };
        }
    }

    // Démarrer le rafraîchissement périodique des partages
    setInterval(loadSharedLinks, 60000); // Toutes les minutes
});

