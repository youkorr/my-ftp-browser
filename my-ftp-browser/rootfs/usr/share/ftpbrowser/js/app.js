document.addEventListener('DOMContentLoaded', function() {
    // Charger la liste des serveurs
    fetch('/api/servers')
        .then(response => response.json())
        .then(data => {
            const serverList = document.getElementById('server-list');
            
            if (data.servers && data.servers.length > 0) {
                let html = '';
                data.servers.forEach((server, index) => {
                    html += `
                        <li class="list-group-item">
                            <i class="bi bi-hdd-network me-2"></i> ${server.name}
                        </li>
                    `;
                });
                serverList.innerHTML = html;
            } else {
                serverList.innerHTML = '<li class="list-group-item">Aucun serveur configuré</li>';
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            document.getElementById('server-list').innerHTML = 
                '<li class="list-group-item text-danger">Erreur de chargement</li>';
        });
});

