let versions = {};

async function makeRequest(url, method, body) {
    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`Server responded with ${response.status}: ${errorData.message}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}

async function getVersions() {
    try {
        versions = await makeRequest('http://localhost:8001/versions', 'POST', {});
        console.log('Versions fetched:', versions);
        populateServerTypes();
    } catch (error) {
        console.error('Error fetching versions:', error);
        showError('Failed to fetch server versions. Please try again later.');
    }
}

function populateServerTypes() {
    const serverTypeSelect = document.getElementById('serverType');
    serverTypeSelect.innerHTML = '<option value="" selected disabled>Select Server Type</option>';
    
    for (const type in versions) {
        const option = document.createElement('option');
        option.value = type.toLowerCase();
        option.textContent = type;
        serverTypeSelect.appendChild(option);
    }

    // Add Custom option
    const customOption = document.createElement('option');
    customOption.value = 'custom';
    customOption.textContent = 'Custom';
    serverTypeSelect.appendChild(customOption);
}

function updateServerVersions() {
    const serverType = document.getElementById('serverType').value;
    const serverVersionSelect = document.getElementById('serverVersion');
    const customJarInput = document.getElementById('customJarInput');
    const versionGroup = document.getElementById('versionGroup');
    const customJarGroup = document.getElementById('customJarGroup');

    if (serverType === 'custom') {
        versionGroup.style.display = 'none';
        customJarGroup.style.display = 'block';
        customJarInput.required = true;
        serverVersionSelect.required = false;
    } else {
        versionGroup.style.display = 'block';
        customJarGroup.style.display = 'none';
        customJarInput.required = false;
        serverVersionSelect.required = true;

        serverVersionSelect.innerHTML = '<option value="" selected disabled>Select Server Version</option>';
        
        if (versions[serverType.charAt(0).toUpperCase() + serverType.slice(1)]) {
            versions[serverType.charAt(0).toUpperCase() + serverType.slice(1)].forEach(version => {
                const option = document.createElement('option');
                option.value = version;
                option.textContent = version;
                serverVersionSelect.appendChild(option);
            });
            serverVersionSelect.disabled = false;
        } else {
            serverVersionSelect.disabled = true;
        }
    }
}

async function createServer(event) {
    event.preventDefault();
    const form = document.getElementById('createServerForm');
    
    if (form.checkValidity()) {
        const serverName = document.getElementById('serverName').value;
        const serverType = document.getElementById('serverType').value;
        const serverVersion = document.getElementById('serverVersion').value;
        const customJarInput = document.getElementById('customJarInput').value;
        const Port = document.getElementById('port').value;
        const minRam = document.getElementById('minRam').value;
        const maxRam = document.getElementById('maxRam').value;
        const maxPlayers = document.getElementById('maxPlayers').value;

        let requestBody = {
            name: serverName,
            type: serverType,
            version: serverVersion,
            port: Port,
            minRam: minRam,
            maxRam: maxRam,
            maxPlayers: maxPlayers
        };

        if (serverType === 'custom') {
            requestBody.jarName = document.getElementById('customJarInput').value;
        } else {
            requestBody.version = document.getElementById('serverVersion').value;
        }

        console.log('Request Body:', requestBody);

        try {
            showLoading();
            const data = await makeRequest('http://localhost:8001/create', 'POST', requestBody);
            hideLoading();
            showSuccess('Server created successfully!');
            form.reset();
        } catch (error) {
            hideLoading();
            showError('Failed to create server: ' + error.message);
        }
    } else {
        form.reportValidity();
    }
}

function showLoading() {
    document.getElementById('createButton').disabled = true;
    document.getElementById('createButton').textContent = 'Creating...';
}

function hideLoading() {
    document.getElementById('createButton').disabled = false;
    document.getElementById('createButton').textContent = 'Create Server';
}

function showSuccess(message) {
    const successElement = document.createElement('div');
    successElement.className = 'success-message';
    successElement.textContent = message;
    document.querySelector('.create-server-form').prepend(successElement);
    setTimeout(() => successElement.remove(), 5000);
}

function showError(message) {
    const errorElement = document.createElement('div');
    errorElement.className = 'error-message';
    errorElement.textContent = message;
    document.querySelector('.create-server-form').prepend(errorElement);
    setTimeout(() => errorElement.remove(), 5000);
}

document.addEventListener('DOMContentLoaded', () => {
    getVersions();
    document.getElementById('createServerForm').addEventListener('submit', createServer);
    document.getElementById('serverType').addEventListener('change', updateServerVersions);
});