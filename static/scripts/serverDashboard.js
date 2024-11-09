// MinecraftWebSocket class for handling WebSocket connections
class MinecraftWebSocket {
    constructor(serverName) {
        this.serverName = serverName;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.handlers = {
            console: [],
            status: []
        };
        this.serverControls = new ServerControls(serverName, 123);
    }

    connect() {
        this.ws = new WebSocket('ws://localhost:8001/ws');
        
        this.ws.onopen = () => {
            console.log('Connected to server');
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            this.triggerHandler('console', 'Connected to server');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'console') {
                appendToTerminal(data.line);
            } else if (data.type === 'metrics') {
                updateMetrics(data.metrics);
            } else if (data.type === 'status') {
                
                updateServerStatus(data.status);
                this.serverControls.updateButtonStates(data.status);
            }
        };

        this.ws.onclose = () => {
            console.log('Disconnected from server');
            this.triggerHandler('console', 'Disconnected from server');
            this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.triggerHandler('console', 'Error: Connection lost');
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            setTimeout(() => {
                this.reconnectAttempts++;
                this.reconnectDelay *= 2;
                this.connect();
            }, this.reconnectDelay);
        }
    }

    sendCommand(command) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                command: command,
                server: this.serverName
            }));
            return true;
        }
        return false;
    }

    on(event, handler) {
        if (this.handlers[event]) {
            this.handlers[event].push(handler);
        }
    }

    triggerHandler(event, data) {
        if (this.handlers[event]) {
            this.handlers[event].forEach(handler => handler(data));
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}
// Server API helper class
class ServerAPI {
    static async makeRequest(url, method, body) {
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

    static async startServer(serverName) {
        try {
            const response = await this.makeRequest('http://localhost:8001/start', 'POST', { server: serverName });
            return response;
        } catch (error) {
            console.error('Start server error:', error);
            throw new Error(error.message || 'Failed to start server');
        }
    }

    static async stopServer(serverName) {
        try {
            const response = await this.makeRequest('http://localhost:8001/stop', 'POST', { server: serverName });
            return response;
        } catch (error) {
            console.error('Stop server error:', error);
            throw new Error(error.message || 'Failed to stop server');
        }
    }

    static async restartServer(serverName) {
        return await this.makeRequest('http://localhost:8001/restart', 'POST', { server: serverName });
    }

    static async deleteServer(serverName) {
        return await this.makeRequest('http://localhost:8001/delete', 'POST', { server: serverName });
    }

    static async acceptEula(serverName) {
        try {
            const response = await this.makeRequest('http://localhost:8001/accept_eula', 'POST', { server: serverName });
            return response;
        } catch (error) {
            console.error('Accept EULA error:', error);
            throw new Error(error.message || 'Failed to accept EULA');
        }
    }

    static async checkIfCreated(serverName) {
        const data = await this.makeRequest('http://localhost:8001/is_created', 'POST', { server: serverName });
        return data.status === true;
    }

}
class ServerControls {
    constructor(serverName, websocket) {
        this.serverName = serverName;
        this.websocket = websocket;
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Start Server Button
        const startButton = document.getElementById('start-server');
        if (startButton) {
            startButton.addEventListener('click', async () => {
                try {
                    startButton.disabled = true;
                    await ServerAPI.startServer(this.serverName);
                    appendToTerminal('Server start command sent successfully');
                } catch (error) {
                    appendToTerminal('Error starting server: ' + error.message);
                } finally {
                    startButton.disabled = false;
                }
            });
        }

        // Stop Server Button
        const stopButton = document.getElementById('stop-server');
        if (stopButton) {
            stopButton.addEventListener('click', async () => {
                try {
                    stopButton.disabled = true;
                    await ServerAPI.stopServer(this.serverName);
                    appendToTerminal('Server stop command sent successfully');
                } catch (error) {
                    appendToTerminal('Error stopping server: ' + error.message);
                } finally {
                    stopButton.disabled = false;
                }
            });
        }

        // Accept EULA Button
        const eulaButton = document.getElementById('accept-eula');
        if (eulaButton) {
            eulaButton.addEventListener('click', async () => {
                try {
                    eulaButton.disabled = true;
                    await ServerAPI.acceptEula(this.serverName);
                    appendToTerminal('EULA accepted successfully');
                } catch (error) {
                    appendToTerminal('Error accepting EULA: ' + error.message);
                } finally {
                    eulaButton.disabled = false;
                }
            });
        }
    }
    // Method to update button states based on server status
    updateButtonStates(status) {
        const startButton = document.getElementById('start-server');
        const stopButton = document.getElementById('stop-server');
        const eulaButton = document.getElementById('accept-eula');

        if (startButton && stopButton) {
            switch (status.toLowerCase()) {
                case 'running':
                    startButton.disabled = true;
                    stopButton.disabled = false;
                    break;
                case 'stopped':
                    startButton.disabled = false;
                    stopButton.disabled = true;
                    break;
                case 'starting':
                case 'stopping':
                    startButton.disabled = true;
                    stopButton.disabled = true;
                    break;
                default:
                    startButton.disabled = false;
                    stopButton.disabled = false;
            }
        }
    }
}

// UI Helper functions
function appendToTerminal(message) {
    const terminalOutput = document.getElementById('terminal-output');
    const line = document.createElement('div');
    line.textContent = message;
    terminalOutput.appendChild(line);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

function updateServerStatus(status) {
    const serverStatus = document.getElementById('serverStatus');
    console.log(status)
    serverStatus.textContent = status.charAt(0).toUpperCase() + status.slice(1);;
    if (status === 'starting' || status === 'stopping') {
        status = 'busy';
    }
    serverStatus.className = "status-indicator " + status;
}

function setupTabSwitching() {
    const tabLinks = document.querySelectorAll('.management-nav a');
    const tabContent = document.getElementById('tab-content');

    tabLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const tab = this.getAttribute('data-tab');
            loadTabContent(tab);
        });
    });

    function loadTabContent(tab) {
        tabContent.innerHTML = `<h2>${tab.charAt(0).toUpperCase() + tab.slice(1)}</h2><p>Content for ${tab} tab.</p>`;
    }
}

// Main initialization
document.addEventListener('DOMContentLoaded', function() {
    const serverName = document.getElementById('serverName')?.textContent;
    if (!serverName) {
        console.error('Server name not found');
        return;
    }

    // Initialize WebSocket connection
    const websocket = new MinecraftWebSocket(serverName);
    
    
    // Connect to WebSocket server
    websocket.connect();
    
    // Set up command input handling
    const commandInput = document.getElementById('command-input');
    const sendCommandBtn = document.getElementById('send-command');
    
    sendCommandBtn.addEventListener('click', function() {
        const command = commandInput.value.trim();
        if (command) {
            if (websocket.sendCommand(command)) {
                appendToTerminal(`> ${command}`);
                commandInput.value = '';
            } else {
                appendToTerminal('Error: Not connected to server');
            }
        }
    });
    
    commandInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendCommandBtn.click();
        }
    });

    // Set up tab switching
    setupTabSwitching();
});