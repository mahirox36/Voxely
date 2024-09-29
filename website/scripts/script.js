let title = document.getElementById('title');

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

function updateTitle(message) {
    title.innerHTML = message;
}

document.getElementById('createButton').addEventListener('click', async function() {
    const requestBody = {
        server: "server1",
        type: "paper",
        version: "1.21.1",
        maxRam: 8192,
    };

    console.log('Request Body:', requestBody);

    try {
        const data = await makeRequest('http://localhost:8001/create', 'POST', requestBody);
        updateTitle("Server is created");
    } catch (error) {
        updateTitle("Failed to create server");
    }
});

document.getElementById('startButton').addEventListener('click', async function() {
    const requestBody = { server: "server1" };

    console.log('Request Body:', requestBody);

    try {
        const data = await makeRequest('http://localhost:8001/start', 'POST', requestBody);
        updateTitle("Server is starting");
    } catch (error) {
        updateTitle("Failed to start server");
    }
});

document.getElementById('stopButton').addEventListener('click', async function() {
    const requestBody = { server: "server1" };

    console.log('Request Body:', requestBody);

    try {
        const data = await makeRequest('http://localhost:8001/stop', 'POST', requestBody);
        updateTitle("Server is stopping");
    } catch (error) {
        updateTitle("Failed to stop server");
    }
});
document.getElementById('acceptButton').addEventListener('click', async function() {
    const requestBody = { server: "server1" };

    console.log('Request Body:', requestBody);

    try {
        const data = await makeRequest('http://localhost:8001/accept_eula', 'POST', requestBody);
        updateTitle("accepting eula");
    } catch (error) {
        updateTitle("Failed to accept eula");
    }
});


async function checkIfCreated() {
    const requestBody = { server: "server1" };

    console.log('Request Body:', requestBody);

    try {
        const data = await makeRequest('http://localhost:8001/is_created', 'POST', requestBody);
        if (data.status === true) {
            updateTitle("Server is created");
        } else {
            updateTitle("Server is not created");
        }
    } catch (error) {
        updateTitle("Failed to check server status");
    }
}

checkIfCreated();