function getSelectedServer() {
    const serverSelect = document.getElementById('serverSelect');
    return serverSelect ? serverSelect.textContent : null;
}

const serverName = getSelectedServer()

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


document.getElementById('startButton').addEventListener('click', async function() {
    const requestBody = { server: serverName };

    console.log('Request Body:', requestBody);

    try {
        const data = await makeRequest('http://localhost:8001/start', 'POST', requestBody);
        return true;
    } catch (error) {
        return false;
    }
});

document.getElementById('stopButton').addEventListener('click', async function() {
    const requestBody = { server: serverName };

    console.log('Request Body:', requestBody);

    try {
        const data = await makeRequest('http://localhost:8001/stop', 'POST', requestBody);
        return true;
    } catch (error) {
        return false;
    }
});
document.getElementById('acceptButton').addEventListener('click', async function() {
    const requestBody = { server: serverName };

    console.log('Request Body:', requestBody);

    try {
        const data = await makeRequest('http://localhost:8001/accept_eula', 'POST', requestBody);
        return true;
    } catch (error) {
        return false;
    }
});


async function checkIfCreated() {
    const requestBody = { server: serverName };

    console.log('Request Body:', requestBody);

    try {
        const data = await makeRequest('http://localhost:8001/is_created', 'POST', requestBody);
        if (data.status === true) {
            return true;
        } else {
            return false;
        }
    } catch (error) {
        return false;
    }
}