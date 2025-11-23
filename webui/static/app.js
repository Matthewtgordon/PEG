/**
 * APEG Dashboard Application
 *
 * WebSocket client and UI logic for APEG real-time monitoring.
 */

// ============================================================================
// WebSocket Client for Real-time Updates
// ============================================================================

class APEGWebSocket {
    constructor() {
        this.ws = null;
        this.reconnectInterval = 5000;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.messageHandlers = {};
        this.pingInterval = null;

        this.connect();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        console.log(`Connecting to WebSocket: ${wsUrl}`);

        try {
            this.ws = new WebSocket(wsUrl);
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.updateConnectionStatus('error');
            return;
        }

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.updateConnectionStatus('connected');

            // Send ping every 30 seconds to keep alive
            this.pingInterval = setInterval(() => {
                this.send({ type: 'ping' });
            }, 30000);

            // Request initial status
            this.send({ type: 'get_status' });
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                console.log('WebSocket message:', message);

                const handler = this.messageHandlers[message.type];
                if (handler) {
                    handler(message);
                }
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        this.ws.onclose = (event) => {
            console.log('WebSocket closed:', event.code);
            this.updateConnectionStatus('disconnected');
            if (this.pingInterval) {
                clearInterval(this.pingInterval);
            }

            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                console.log(`Reconnecting in ${this.reconnectInterval}ms (attempt ${this.reconnectAttempts})`);
                setTimeout(() => this.connect(), this.reconnectInterval);
            } else {
                this.updateConnectionStatus('failed');
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }

    on(messageType, handler) {
        this.messageHandlers[messageType] = handler;
    }

    updateConnectionStatus(status) {
        const statusElement = document.getElementById('ws-status');
        if (!statusElement) return;

        const indicator = statusElement.querySelector('.status-indicator');
        const text = statusElement.querySelector('.status-text');
        if (!indicator || !text) return;

        switch (status) {
            case 'connected':
                indicator.className = 'status-indicator status-connected';
                text.textContent = 'Connected';
                break;
            case 'disconnected':
                indicator.className = 'status-indicator status-disconnected';
                text.textContent = 'Disconnected';
                break;
            case 'error':
            case 'failed':
                indicator.className = 'status-indicator status-error';
                text.textContent = 'Failed';
                break;
            default:
                indicator.className = 'status-indicator';
                text.textContent = 'Connecting...';
        }
    }
}

// ============================================================================
// Dashboard State & UI Elements
// ============================================================================

let apegWS = null;
let isRunning = false;

// ============================================================================
// Status Update Handlers
// ============================================================================

function updateDashboard(statusData) {
    if (!statusData) return;

    // Update system health
    const healthBadge = document.querySelector('#system-health .health-badge');
    if (healthBadge) {
        healthBadge.textContent = statusData.system_health || 'Unknown';
        healthBadge.className = `health-badge health-${statusData.system_health || 'unknown'}`;
    }

    // Update agent count
    const agentCount = Object.keys(statusData.agents || {}).length;
    const activeAgentsEl = document.getElementById('active-agents-count');
    if (activeAgentsEl) {
        activeAgentsEl.textContent = agentCount;
    }

    // Update agent list
    const agentListEl = document.getElementById('agent-list');
    if (agentListEl && statusData.agents) {
        const agentNames = Object.values(statusData.agents)
            .map(a => a.name)
            .join(', ');
        agentListEl.textContent = agentNames || 'None';
    }

    // Update test mode status
    const testModeEl = document.getElementById('test-mode-status');
    if (testModeEl) {
        testModeEl.textContent = statusData.test_mode ? 'ON' : 'OFF';
    }

    // Update uptime
    const uptimeEl = document.getElementById('uptime');
    if (uptimeEl) {
        const minutes = Math.floor((statusData.uptime_seconds || 0) / 60);
        uptimeEl.textContent = minutes;
    }

    // Update agent status grid
    updateAgentGrid(statusData.agents || {});
}

function updateAgentGrid(agents) {
    const gridEl = document.getElementById('agent-status-grid');
    if (!gridEl) return;

    if (Object.keys(agents).length === 0) {
        return;
    }

    let html = '';
    for (const [agentId, agent] of Object.entries(agents)) {
        const statusClass = agent.status === 'available' ? 'status-active' : 'status-inactive';
        const modeLabel = agent.test_mode ? 'Test Mode' : 'Production';

        html += `
            <div class="agent-card ${statusClass}">
                <div class="agent-header">
                    <h4>${agent.name}</h4>
                    <span class="agent-status-badge">${agent.status}</span>
                </div>
                <div class="agent-details">
                    <p class="agent-mode">${modeLabel}</p>
                </div>
            </div>
        `;
    }

    gridEl.innerHTML = html;
}

function addWorkflowToRecent(workflowData) {
    const listEl = document.getElementById('recent-workflows');
    if (!listEl) return;

    const emptyState = listEl.querySelector('.empty-state');
    if (emptyState) {
        emptyState.remove();
    }

    const item = document.createElement('div');
    item.className = 'workflow-item';

    const timestamp = new Date(workflowData.timestamp || Date.now()).toLocaleString();
    const statusClass = workflowData.status === 'success' ? 'status-success' : 'status-warning';

    item.innerHTML = `
        <div class="workflow-header">
            <span class="workflow-id">${workflowData.id || 'N/A'}</span>
            <span class="workflow-status ${statusClass}">${workflowData.status || 'unknown'}</span>
        </div>
        <div class="workflow-details">
            <p>${workflowData.description || 'Workflow execution'}</p>
            <p class="workflow-timestamp">${timestamp}</p>
        </div>
    `;

    listEl.insertBefore(item, listEl.firstChild);

    while (listEl.children.length > 10) {
        listEl.removeChild(listEl.lastChild);
    }
}

// ============================================================================
// Workflow Execution
// ============================================================================

async function runWorkflow() {
    const goalEl = document.getElementById('goal');
    const outputEl = document.getElementById('output');
    const statusEl = document.getElementById('status');
    const runBtn = document.getElementById('run-btn');

    const goal = goalEl ? goalEl.value.trim() : '';
    if (!goal) {
        if (statusEl) {
            statusEl.textContent = 'Please enter a goal';
            statusEl.className = 'status error';
        }
        return;
    }

    if (isRunning) return;

    isRunning = true;
    if (runBtn) {
        runBtn.disabled = true;
        runBtn.textContent = 'Running...';
    }
    if (statusEl) {
        statusEl.textContent = 'Running...';
        statusEl.className = 'status loading';
    }
    if (outputEl) {
        outputEl.textContent = 'Executing workflow...';
    }

    try {
        const response = await fetch('/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                goal: goal,
                workflow_path: 'WorkflowGraph.json'
            })
        });

        const result = await response.json();

        if (result.status === 'success') {
            if (outputEl) {
                outputEl.textContent = result.final_output || 'Workflow completed successfully';
            }
            if (statusEl) {
                statusEl.textContent = 'Success';
                statusEl.className = 'status success';
            }

            const successFlag = document.getElementById('success-flag');
            const scoreValue = document.getElementById('score-value');
            const stepsCount = document.getElementById('steps-count');
            const debugEl = document.getElementById('debug');

            if (successFlag) successFlag.textContent = 'Yes';
            if (scoreValue) scoreValue.textContent = result.score ? result.score.toFixed(2) : 'N/A';
            if (stepsCount) stepsCount.textContent = result.history ? result.history.length : 'N/A';
            if (debugEl) debugEl.textContent = JSON.stringify(result.history || result.state || {}, null, 2);

            const workflowsEl = document.getElementById('workflows-count');
            if (workflowsEl) {
                workflowsEl.textContent = parseInt(workflowsEl.textContent || '0') + 1;
            }

            addWorkflowToRecent({
                id: Date.now().toString(36),
                status: 'success',
                description: goal.substring(0, 50) + (goal.length > 50 ? '...' : ''),
                timestamp: new Date().toISOString()
            });
        } else {
            if (outputEl) {
                outputEl.textContent = result.error || 'Workflow failed';
            }
            if (statusEl) {
                statusEl.textContent = 'Error';
                statusEl.className = 'status error';
            }

            const debugEl = document.getElementById('debug');
            if (debugEl) debugEl.textContent = JSON.stringify(result, null, 2);
        }
    } catch (error) {
        if (outputEl) {
            outputEl.textContent = `Error: ${error.message}`;
        }
        if (statusEl) {
            statusEl.textContent = 'Error';
            statusEl.className = 'status error';
        }
        console.error('Workflow error:', error);
    } finally {
        isRunning = false;
        if (runBtn) {
            runBtn.disabled = false;
            runBtn.textContent = 'Run APEG';
        }
    }
}

function clearOutput() {
    const goalEl = document.getElementById('goal');
    const outputEl = document.getElementById('output');
    const statusEl = document.getElementById('status');
    const successFlag = document.getElementById('success-flag');
    const scoreValue = document.getElementById('score-value');
    const stepsCount = document.getElementById('steps-count');
    const debugEl = document.getElementById('debug');

    if (goalEl) goalEl.value = '';
    if (outputEl) outputEl.textContent = 'Waiting for workflow execution...';
    if (statusEl) {
        statusEl.textContent = '';
        statusEl.className = 'status';
    }
    if (successFlag) successFlag.textContent = '-';
    if (scoreValue) scoreValue.textContent = '-';
    if (stepsCount) stepsCount.textContent = '-';
    if (debugEl) debugEl.textContent = 'No execution data yet.';
}

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('APEG Dashboard loaded');

    // Initialize WebSocket
    apegWS = new APEGWebSocket();

    // Register WebSocket handlers
    apegWS.on('status_update', (message) => {
        updateDashboard(message.data);
    });

    apegWS.on('workflow_event', (message) => {
        addWorkflowToRecent(message.data);
    });

    apegWS.on('connection', (message) => {
        console.log('WebSocket connection confirmed:', message);
    });

    apegWS.on('pong', () => {
        console.log('Heartbeat received');
    });

    // Bind button events
    const runBtn = document.getElementById('run-btn');
    const clearBtn = document.getElementById('clear-btn');

    if (runBtn) {
        runBtn.addEventListener('click', runWorkflow);
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', clearOutput);
    }

    // Allow Ctrl+Enter to run workflow
    const goalEl = document.getElementById('goal');
    if (goalEl) {
        goalEl.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                runWorkflow();
            }
        });
    }

    // Initial health check
    fetch('/health')
        .then(res => res.json())
        .then(data => {
            console.log('APEG API Health:', data);
        })
        .catch(err => {
            console.warn('Health check failed:', err);
        });
});
