/**
 * My FTP Browser - Application JavaScript
 */

// État global de l'application
const state = {
    currentPath: '/',
    items: [],
    allowUpload: true,
    allowDelete: true
};

// Éléments DOM
const elements = {
    currentPath: document.getElementById('current-path'),
    fileList: document.getElementById('file-list'),
    loading: document.getElementById('loading'),
    emptyMessage: document.getElementById('empty-message'),
    errorMessage: document.getElementById('error-message'),
    errorText: document.getElementById('error-text'),
    modal: document.getElementById('modal'),
    modalTitle: document.getElementById('modal-title'),
    modalBody: document.getElementById('modal-body'),
    modalCancel: document.getElementById('modal-cancel'),
    modalConfirm: document.getElementById('modal-confirm'),
    btnUpload: document.getElementById('btn-upload'),
    btnMkdir: document.getElementById('btn-mkdir'),
    btnRefresh: document.getElementById('btn-refresh'),
    fileUpload: document.getElementById('file-upload')
};

// Gestionnaires d'événements
function setupEventListeners() {
    // Boutons principaux
    elements.btnRefresh.addEventListener('click', refreshCurrentDirectory);
    elements.btnUpload.addEventListener('click', () => elements.fileUpload.click());
    elements.btnMkdir.addEventListener('click', showCreateDirectoryModal);
    elements.fileUpload.addEventListener('change', handleFileUpload);
    
    // Modal
    document.querySelector('.close').addEventListener('click', closeModal);
    elements.modalCancel.addEventListener('click', closeModal);
    
    // Fermer le modal en cliquant en dehors
    window.addEventListener('click', (event) => {
        if (event.target === elements.modal) {
            closeModal();
        }
    });
}

// Charger le répertoire courant
async function loadDirectory(path = '/') {
    try {
        showLoading();
        hideError();
        
        const response = await fetch('/api/list', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ path }),
        });
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Erreur lors du chargement du répertoire');
        }
        
        state.currentPath = data.path;
        state.items = data.items;
        
        updateUI();
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

// Mettre à jour l'interface utilisateur
function updateUI() {
    // Mettre à jour le chemin actuel
    elements.currentPath.textContent = state.currentPath;
    
    // Vider la liste de fichiers
    elements.fileList.innerHTML = '';
    
    // Ajouter le dossier parent si nous ne sommes pas à la racine
    if (state.currentPath !== '/') {
        const parentItem = createFileItem({
            name: '..',
            isDirectory: true,
            size: '',
            date: ''
        }, true);
        
        elements.fileList.appendChild(parentItem);
    }
    
    // Si la liste est vide (et que nous ne sommes pas à la racine), afficher le message d'erreur
    if (state.items.length === 0) {
        showEmptyMessage();
        return;
    }
    
    // Cacher le message vide
    hideEmptyMessage();
    
    // Ajouter chaque élément à la liste
    state.items.forEach(item => {
        const fileItem = createFileItem(item);
        elements.fileList.appendChild(fileItem);
    });
}

// Créer un élément de fichier
function createFileItem(item, isParent = false) {
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    
    const iconClass = item.isDirectory ? 'folder' : getFileIconClass(item.name);
    
    fileItem.innerHTML = `
        <div class="file-icon ${iconClass}">
            <i class="fas ${item.isDirectory ? 'fa-folder' : 'fa-file'}"></i>
        </div>
        <div class="file-details">
            <div class="file-name">${item.name}</div>
            <div class="file-info">
                ${item.size ? `<span class="file-size">${formatSize(item.size)}</span>` : ''}
                ${item.date ? `<span class="file-date">${item.date}</span>` : ''}
            </div>
        </div>
        ${isParent ? '' : `
        <div class="file-actions">
            ${!item.isDirectory ? `
            <button class="file-action download" title="Télécharger">
                <i class="fas fa-download"></i>
            </button>
            ` : ''}
            <button class="file-action rename" title="Renommer">
                <i class="fas fa-edit"></i>
            </button>
            <button class="file-action delete" title="Supprimer">
                <i class="fas fa-trash"></i>
            </button>
        </div>
        `}
    `;
    
    // Ajouter les gestionnaires d'événements
    const fileName = fileItem.querySelector('.file-name');
    fileName.addEventListener('click', () => {
        if (item.isDirectory) {
            navigateToDirectory(isParent ? getParentPath(state.currentPath) : `${state.currentPath}${state.currentPath.endsWith('/') ? '' : '/'}${item.name}`);
        } else {
            downloadFile(item.name);
        }
    });
    
    // Ajouter les gestionnaires pour les actions seulement si ce n'est pas le dossier parent
    if (!isParent) {
        const downloadBtn = fileItem.querySelector('.file-action.download');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => downloadFile(item.name));
        }
        
        const renameBtn = fileItem.querySelector('.file-action.rename');
        if (renameBtn) {
            renameBtn.addEventListener('click', () => showRenameModal(item.name));
        }
        
        const deleteBtn = fileItem.querySelector('.file-action.delete');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => showDeleteConfirmation(item.name, item.isDirectory));
        }
    }
    
    return fileItem;
}

// Obtenir la classe d'icône en fonction de l'extension du fichier
function getFileIconClass(filename) {
    const extension = filename.split('.').pop().toLowerCase();
    
    const iconMapping = {
        pdf: 'fa-file-pdf',
        doc: 'fa-file-word',
        docx: 'fa-file-word',
        xls: 'fa-file-excel',
        xlsx: 'fa-file-excel',
        ppt: 'fa-file-powerpoint',
        pptx: 'fa-file-powerpoint',
        jpg: 'fa-file-image',
        jpeg: 'fa-file-image',
        png: 'fa-file-image',
        gif: 'fa-file-image',
        svg: 'fa-file-image',
        mp3: 'fa-file-audio',
        wav: 'fa-file-audio',
        mp4: 'fa-file-video',
        mov: 'fa-file-video',
        zip: 'fa-file-archive',
        rar: 'fa-file-archive',
        txt: 'fa-file-alt',
        js: 'fa-file-code',
        py: 'fa-file-code',
        html: 'fa-file-code',
        css: 'fa-file-code',
        json: 'fa-file-code'
    };
    
    return iconMapping[extension] || 'fa-file';
}

// Formater la taille du fichier
function formatSize(size) {
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let formattedSize = parseInt(size, 10);
    let unitIndex = 0;
    
    while (formattedSize >= 1024 && unitIndex < units.length - 1) {
        formattedSize /= 1024;
        unitIndex++;
    }
    
    return `${formattedSize.toFixed(1)} ${units[unitIndex]}`;
}

// Obtenir le chemin parent
function getParentPath(path) {
    if (path === '/' || !path) return '/';
    
    const parts = path.split('/').filter(part => part !== '');
    parts.pop();
    
    return parts.length === 0 ? '/' : `/${parts.join('/')}/`;
}

// Naviguer vers un répertoire
function navigateToDirectory(path) {
    loadDirectory(path);
}

// Actualiser le répertoire courant
function refreshCurrentDirectory() {
    loadDirectory(state.currentPath);
}

// Télécharger un fichier
async function downloadFile(filename) {
    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                path: state.currentPath,
                filename: filename
            }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Erreur lors du téléchargement du fichier');
        }
        
        // Créer un lien de téléchargement
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    } catch (error) {
        showError(error.message);
    }
}

// Afficher le modal de confirmation de suppression
function showDeleteConfirmation(name, isDirectory) {
    elements.modalTitle.textContent = `Supprimer ${isDirectory ? 'le dossier' : 'le fichier'}`;
    elements.modalBody.innerHTML = `
        <p>Êtes-vous sûr de vouloir supprimer ${isDirectory ? 'le dossier' : 'le fichier'} <strong>${name}</strong> ?</p>
        ${isDirectory ? '<p class="warning"><i class="fas fa-exclamation-triangle"></i> Cette action supprimera également tous les fichiers et sous-dossiers contenus.</p>' : ''}
    `;
    
    elements.modalConfirm.className = 'btn btn-danger';
    elements.modalConfirm.textContent = 'Supprimer';
    
    elements.modalConfirm.onclick = async () => {
        try {
            const response = await fetch('/api/delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    path: state.currentPath,
                    name: name,
                    isDirectory: isDirectory
                }),
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Erreur lors de la suppression');
            }
            
            closeModal();
            refreshCurrentDirectory();
        } catch (error) {
            showError(error.message);
            closeModal();
        }
    };
    
    openModal();
}

// Afficher le modal de création de répertoire
function showCreateDirectoryModal() {
    elements.modalTitle.textContent = 'Créer un nouveau dossier';
    elements.modalBody.innerHTML = `
        <label for="directory-name">Nom du dossier :</label>
        <input type="text" id="directory-name" placeholder="Nouveau dossier">
    `;
    
    elements.modalConfirm.className = 'btn btn-primary';
    elements.modalConfirm.textContent = 'Créer';
    
    elements.modalConfirm.onclick = async () => {
        const directoryName = document.getElementById('directory-name').value.trim();
        
        if (!directoryName) {
            alert('Veuillez entrer un nom de dossier');
            return;
        }
        
        try {
            const response = await fetch('/api/mkdir', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    path: state.currentPath,
                    name: directoryName
                }),
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Erreur lors de la création du dossier');
            }
            
            closeModal();
            refreshCurrentDirectory();
        } catch (error) {
            showError(error.message);
            closeModal();
        }
    };
    
    openModal();
    
    // Focus sur le champ de saisie
    setTimeout(() => {
        document.getElementById('directory-name').focus();
    }, 100);
}

// Afficher le modal de renommage
function showRenameModal(name) {
    elements.modalTitle.textContent = 'Renommer';
    elements.modalBody.innerHTML = `
        <label for="new-name">Nouveau nom :</label>
        <input type="text" id="new-name" value="${name}">
    `;
    
    elements.modalConfirm.className = 'btn btn-primary';
    elements.modalConfirm.textContent = 'Renommer';
    
    elements.modalConfirm.onclick = async () => {
        const newName = document.getElementById('new-name').value.trim();
        
        if (!newName) {
            alert('Veuillez entrer un nom');
            return;
        }
        
        try {
            const response = await fetch('/api/rename', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    path: state.currentPath,
                    oldName: name,
                    newName: newName
                }),
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Erreur lors du renommage');
            }
            
            closeModal();
            refreshCurrentDirectory();
        } catch (error) {
            showError(error.message);
            closeModal();
        }
    };
    
    openModal();
    
    // Focus sur le champ de saisie
    setTimeout(() => {
        const input = document.getElementById('new-name');
        input.focus();
        input.setSelectionRange(0, input.value.length);
    }, 100);
}

// Gérer l'upload de fichiers
async function handleFileUpload(event) {
    const files = event.target.files;
    
    if (!files.length) return;
    
    try {
        showLoading();
        
        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('path', state.currentPath);
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData,
            });
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || `Erreur lors de l'upload de ${file.name}`);
            }
        }
        
        // Réinitialiser l'élément input file
        event.target.value = '';
        
        // Rafraîchir le répertoire courant
        refreshCurrentDirectory();
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

// Fonctions d'interface utilisateur
function showLoading() {
    elements.loading.style.display = 'block';
    elements.fileList.style.display = 'none';
}

function hideLoading() {
    elements.loading.style.display = 'none';
    elements.fileList.style.display = 'block';
}

function showEmptyMessage() {
    elements.emptyMessage.style.display = 'block';
    elements.fileList.style.display = 'none';
}

function hideEmptyMessage() {
    elements.emptyMessage.style.display = 'none';
    elements.fileList.style.display = 'block';
}

function showError(message) {
    elements.errorText.textContent = message;
    elements.errorMessage.style.display = 'block';
    elements.fileList.style.display = 'none';
    elements.emptyMessage.style.display = 'none';
}

function hideError() {
    elements.errorMessage.style.display = 'none';
}

function openModal() {
    elements.modal.style.display = 'block';
}

function closeModal() {
    elements.modal.style.display = 'none';
}

// Initialiser l'application
function init() {
    setupEventListeners();
    loadDirectory('/');
}

// Démarrer l'application quand le DOM est chargé
document.addEventListener('DOMContentLoaded', init);
