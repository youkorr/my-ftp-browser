document.addEventListener('DOMContentLoaded', function() {
    // Charger les serveurs
    fetch('/api/servers')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            const serverList = document.getElementById('server-list');
            
            if (data.servers && data.servers.length > 0) {
                let html = '<ul class="list-group">';
                data.servers.forEach(server => {
                    html += `
                        <li class="list-group-item server-item" data-id="${server.id}">
                            ${server.name}
                            <div class="text-muted small">${server.host}:${server.port}</div>
                        </li>
                    `;
                });
                html += '</ul>';
                serverList.innerHTML = html;
                
                // Ajouter des événements click
                document.querySelectorAll('.server-item').forEach(item => {
                    item.addEventListener('click', function() {
                        const serverId = this.getAttribute('data-id');
                        selectServer(serverId);
                    });
                });
            } else {
                serverList.innerHTML = '<div class="alert alert-warning">No servers configured</div>';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('server-list').innerHTML = 
                `<div class="alert alert-danger">Error: ${error.message}</div>`;
        });
    
    // Fonction pour sélectionner un serveur
    function selectServer(serverId) {
        // Retirer la classe active de tous les serveurs
        document.querySelectorAll('.server-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Ajouter la classe active au serveur sélectionné
        document.querySelector(`.server-item[data-id="${serverId}"]`).classList.add('active');
        
        // Afficher un message de fonctionnalité à venir
        document.getElementById('file-browser').innerHTML = `
            <div class="text-center py-5">
                <h3>Server ${serverId} selected</h3>
                <p>Coming soon: Full FTP browsing functionality</p>
                <div class="alert alert-info mt-3">
                    This is a minimal working example.<br>
                    The complete FTP browser functionality will be implemented in the next version.
                </div>
            </div>
        `;
    }
    
    // Vérifier la santé de l'API périodiquement
    function checkApiHealth() {
        fetch('/api/health')
            .then(response => response.json())
            .then(data => {
                console.log('API Health:', data);
            })
            .catch(error => {
                console.error('API Health Check Error:', error);
            });
    }
    
    // Vérifier la santé toutes les 30 secondes
    setInterval(checkApiHealth, 30000);
    checkApiHealth(); // Vérifier immédiatement au démarrage
});
