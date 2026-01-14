// DOM Elements
const agentsList = document.getElementById('agentsList');
const addAgentBtn = document.getElementById('addAgentBtn');
const agentModal = document.getElementById('agentModal');
const closeAgentModalBtn = document.getElementById('closeAgentModalBtn');
const saveAgentBtn = document.getElementById('saveAgentBtn');
const agentNameInput = document.getElementById('agentNameInput');
const agentFolderIdInput = document.getElementById('agentFolderIdInput');
const agentFolderDisplayInput = document.getElementById('agentFolderDisplayInput');
const agentMsg = document.getElementById('agentMsg');

const agentBrowseBtn = document.getElementById('agentBrowseBtn');
const agentModalTitle = document.getElementById('agentModalTitle');

// Agent LLM Elements
const agentLlmProvider = document.getElementById('agentLlmProvider');
const agentOllamaConfig = document.getElementById('agentOllamaConfig');
const agentOllamaBaseUrl = document.getElementById('agentOllamaBaseUrl');
const agentOllamaModel = document.getElementById('agentOllamaModel');

let editingAgentId = null; // null means adding new agent

// State
let currentAgentId = 'default';
let agents = [];
const openSettingsBtn = document.getElementById('openSettingsBtn');
const settingsModal = document.getElementById('settingsModal');
const closeSettingsBtn = document.getElementById('closeSettingsBtn');
const saveSettingsBtn = document.getElementById('saveSettingsBtn');
const llmProvider = document.getElementById('llmProvider');
const ollamaConfig = document.getElementById('ollamaConfig');
const ollamaBaseUrl = document.getElementById('ollamaBaseUrl');
const ollamaModel = document.getElementById('ollamaModel');
const settingsMsg = document.getElementById('settingsMsg');
const saveConfigBtn = document.getElementById('saveConfigBtn');
const ingestBtn = document.getElementById('ingestBtn');
const statusLog = document.getElementById('statusLog');
const chatHistory = document.getElementById('chatHistory');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');

// Helper to log messages
function log(msg) {
    if (statusLog) {
        const div = document.createElement('div');
        div.innerText = `> ${msg}`;
        statusLog.appendChild(div);
        statusLog.scrollTop = statusLog.scrollHeight;
    } else {
        console.log(`[Log]: ${msg}`);
    }
}

// Global Error Handler
window.onerror = function (msg, url, lineNo, columnNo, error) {
    const string = msg.toLowerCase();
    const substring = "script error";
    if (string.indexOf(substring) > -1) {
        alert('Script Error: See Console for details.');
    } else {
        const message = [
            'Message: ' + msg,
            'URL: ' + url,
            'Line: ' + lineNo,
            'Column: ' + columnNo,
            'Error object: ' + JSON.stringify(error)
        ].join(' - ');

        console.error(message);
        // Try to show in UI
        if (agentsList) {
            agentsList.innerHTML = `<div style="color: red; padding: 10px; font-size: 0.8rem;">System Error: ${msg} <br> Line: ${lineNo}</div>`;
        }
    }
    return false;
};

// Helper to add chat message
function addMessage(text, type, sources = []) {
    const div = document.createElement('div');
    div.className = `message ${type}`;

    let content = `<div>${text}</div>`;

    if (sources && sources.length > 0) {
        // Unique sources
        // Unique sources
        const uniqueSources = [...new Set(sources)];
        const sourceLinks = uniqueSources.map(s => {
            const filename = s.split('/').pop();
            return `<a href="/files/${encodeURIComponent(filename)}" target="_blank" style="color: #4ade80; text-decoration: underline;">${filename}</a>`;
        });
        content += `<div class="sources">Sources: ${sourceLinks.join(', ')}</div>`;
    }

    div.innerHTML = content;
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    return div;
}

// Helper to add typing indicator
function addTypingIndicator() {
    const div = document.createElement('div');
    div.className = 'typing-indicator';
    div.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    return div;
}

// --- Agent Management ---

async function loadAgents() {
    try {
        log('Fetching agents...');
        // Add cache buster
        const res = await fetch(`/api/agents?t=${Date.now()}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        agents = await res.json();
        console.log('Agents loaded:', agents);

        if (!Array.isArray(agents)) {
            throw new Error('Agents response is not an array');
        }

        renderAgents();
        log(`Loaded ${agents.length} agents.`);

        // Ensure current agent exists, if not fallback to first
        if (!agents.find(a => a.id === currentAgentId) && agents.length > 0) {
            currentAgentId = agents[0].id;
        }
    } catch (e) {
        console.error('Error loading agents:', e);
        log(`Error loading agents: ${e.message}`);
        agentsList.innerHTML = `<div style="color: red; font-size: 0.8rem; text-align: center;">Error: ${e.message}</div>`;
    }
}

function renderAgents() {
    agentsList.innerHTML = '';

    if (agents.length === 0) {
        agentsList.innerHTML = '<div style="text-align: center; color: #888; font-size: 0.8rem;">No agents found. Add one!</div>';
        return;
    }

    agents.forEach(agent => {
        const div = document.createElement('div');
        const isActive = agent.id === currentAgentId;

        div.style.cssText = `
            padding: 0.5rem; 
            border-radius: 6px; 
            cursor: pointer; 
            background: ${isActive ? 'rgba(255, 255, 255, 0.1)' : 'transparent'};
            border: 1px solid ${isActive ? 'rgba(255, 255, 255, 0.2)' : 'transparent'};
            transition: all 0.2s;
        `;

        div.innerHTML = `
            <div style="flex-grow: 1;">
                <div style="font-size: 0.9rem; font-weight: 500;">${agent.name}</div>
                <div style="font-size: 0.7rem; color: rgba(255,255,255,0.5); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    ${agent.folder_name || '...' + agent.folder_id.slice(-6)}
                </div>
            </div>
            <button class="edit-agent-btn" style="background: none; border: none; color: rgba(255,255,255,0.5); cursor: pointer; padding: 2px;" title="Configure Agent">⚙️</button>
        `;

        div.querySelector('div').addEventListener('click', () => {
            currentAgentId = agent.id;
            renderAgents();
            log(`Switched to agent: ${agent.name}`);
            chatHistory.innerHTML = ''; // Clear chat on switch? Maybe optional.
            addMessage(`Switched to ${agent.name}. How can I help?`, 'ai');
        });

        div.querySelector('.edit-agent-btn').addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent switching
            openEditAgentModal(agent);
        });

        agentsList.appendChild(div);
    });
}

// Add Agent Logic
addAgentBtn.addEventListener('click', () => {
    editingAgentId = null;
    agentModalTitle.innerText = "Add New Agent";
    agentNameInput.value = '';
    agentNameInput.disabled = false; // Allow name editing for new agents
    agentFolderIdInput.value = '';
    agentFolderDisplayInput.value = '';

    // Reset LLM defaults
    agentLlmProvider.value = 'gemini';
    toggleAgentOllamaConfig();
    agentOllamaBaseUrl.value = 'http://localhost:11434';
    agentOllamaModel.value = 'llama3';

    agentModal.style.display = 'flex';
});

function openEditAgentModal(agent) {
    editingAgentId = agent.id;
    agentModalTitle.innerText = "Edit Agent";
    agentNameInput.value = agent.name;
    agentNameInput.disabled = true; // ID is derived from name, so maybe don't allow renaming to keep it simple? Or allow renaming but keep ID? Let's disable for now to avoid ID logic complexity.
    agentFolderIdInput.value = agent.folder_id;
    agentFolderDisplayInput.value = agent.folder_name || '';

    // Load LLM Config
    if (agent.llm_config) {
        agentLlmProvider.value = agent.llm_config.provider || 'gemini';
        agentOllamaBaseUrl.value = agent.llm_config.ollama_base_url || 'http://localhost:11434';
        agentOllamaModel.value = agent.llm_config.ollama_model || 'llama3';
    } else {
        // Defaults
        agentLlmProvider.value = 'gemini';
        agentOllamaBaseUrl.value = 'http://localhost:11434';
        agentOllamaModel.value = 'llama3';
    }
    toggleAgentOllamaConfig();

    agentModal.style.display = 'flex';
}

closeAgentModalBtn.addEventListener('click', () => {
    agentModal.style.display = 'none';
    agentMsg.innerText = '';
});

// Reuse browser logic for Agent Modal
agentBrowseBtn.addEventListener('click', () => {
    // We reuse the global browser modal but need to know it's for the agent form
    window.browserTarget = 'agent';
    browserModal.style.display = 'flex';
    loadFolders('root');
});

saveAgentBtn.addEventListener('click', async () => {
    const name = agentNameInput.value.trim();
    const folderId = agentFolderIdInput.value.trim();
    const folderName = agentFolderDisplayInput.value;

    if (!name || !folderId) {
        agentMsg.innerText = 'Name and Folder are required.';
        agentMsg.style.color = 'red';
        return;
    }

    agentMsg.innerText = 'Saving...';
    agentMsg.style.color = '#ccc';

    const id = editingAgentId ? editingAgentId : name.toLowerCase().replace(/[^a-z0-9]/g, '-');

    const agentData = {
        id: id,
        name: name,
        folder_id: folderId,
        folder_name: folderName,
        llm_config: {
            provider: agentLlmProvider.value,
            ollama_base_url: agentOllamaBaseUrl.value,
            ollama_model: agentOllamaModel.value
        }
    };

    try {
        const res = await fetch('/api/agents', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(agentData)
        });

        const data = await res.json();
        agentMsg.innerText = 'Agent created!';
        agentMsg.style.color = '#4ade80';

        loadAgents(); // Refresh list

        setTimeout(() => {
            agentModal.style.display = 'none';
            agentMsg.innerText = '';
        }, 1000);

    } catch (e) {
        agentMsg.innerText = 'Error creating agent.';
        agentMsg.style.color = 'red';
    }

});

// Toggle Ollama fields in Agent Modal
if (agentLlmProvider) {
    agentLlmProvider.addEventListener('change', toggleAgentOllamaConfig);
}

function toggleAgentOllamaConfig() {
    if (agentOllamaConfig && agentLlmProvider) {
        agentOllamaConfig.style.display = agentLlmProvider.value === 'ollama' ? 'block' : 'none';
    }
}

// Settings Logic
// Settings Logic
if (openSettingsBtn) {
    openSettingsBtn.addEventListener('click', async () => {
        // Load settings
        const res = await fetch('/api/settings');
        const settings = await res.json();

        if (llmProvider) llmProvider.value = settings.llm_provider || 'gemini';
        if (ollamaBaseUrl) ollamaBaseUrl.value = settings.ollama_base_url || 'http://localhost:11434';
        if (ollamaModel) ollamaModel.value = settings.ollama_model || 'llama3';

        if (llmProvider) toggleOllamaConfig();
        if (settingsModal) settingsModal.style.display = 'flex';
    });
}

closeSettingsBtn.addEventListener('click', () => {
    settingsModal.style.display = 'none';
    settingsMsg.innerText = '';
});

if (llmProvider) {
    llmProvider.addEventListener('change', toggleOllamaConfig);
}

function toggleOllamaConfig() {
    if (ollamaConfig && llmProvider) {
        ollamaConfig.style.display = llmProvider.value === 'ollama' ? 'block' : 'none';
    }
}

saveSettingsBtn.addEventListener('click', async () => {
    settingsMsg.innerText = 'Saving...';
    settingsMsg.style.color = '#ccc';

    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                llm_provider: llmProvider.value,
                ollama_base_url: ollamaBaseUrl.value,
                ollama_model: ollamaModel.value
            })
        });
        const data = await res.json();
        settingsMsg.innerText = data.message;
        settingsMsg.style.color = '#4ade80'; // green

        setTimeout(() => {
            settingsModal.style.display = 'none';
            settingsMsg.innerText = '';
        }, 1500);

        log('Systems updated: RAG Chain reloaded with new settings.');

    } catch (e) {
        settingsMsg.innerText = 'Error saving settings';
        settingsMsg.style.color = '#ef4444'; // red
    }
});

// DEPRECATED: Old Save Config Config logic removed
// saveConfigBtn was removed from HTML

// Trigger Ingestion
ingestBtn.addEventListener('click', async () => {
    log('Starting ingestion process...');
    ingestBtn.disabled = true;
    ingestBtn.style.opacity = '0.7';

    try {
        const res = await fetch('/api/ingest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent_id: currentAgentId })
        });
        const data = await res.json();
        log(data.message);
        log('(Check server terminal for detailed progress)');
    } catch (e) {
        log('Error starting ingestion.');
    } finally {
        setTimeout(() => {
            ingestBtn.disabled = false;
            ingestBtn.style.opacity = '1';
        }, 2000);

        // Start polling
        pollIngestionStatus();
    }
});

let pollingInterval;

function pollIngestionStatus() {
    if (pollingInterval) clearInterval(pollingInterval);

    const statusDiv = document.createElement('div');
    statusDiv.id = 'ingestStatusDisplay';
    statusDiv.style.cssText = 'margin-top: 10px; font-size: 0.8rem; color: #fff; text-align: center;';

    // Replace or append
    const existing = document.getElementById('ingestStatusDisplay');
    if (existing) existing.remove();

    ingestBtn.parentNode.appendChild(statusDiv);

    pollingInterval = setInterval(async () => {
        try {
            const res = await fetch(`/api/ingest/status?agent_id=${currentAgentId}`);
            const data = await res.json();

            statusDiv.innerText = `${data.status.toUpperCase()}: ${data.message}`;

            if (data.status === 'processing') {
                statusDiv.style.color = '#fbbf24'; // yellow
                ingestBtn.disabled = true;
                ingestBtn.style.opacity = '0.7';
            } else if (data.status === 'completed') {
                statusDiv.style.color = '#4ade80'; // green
                ingestBtn.disabled = false;
                ingestBtn.style.opacity = '1';
                setTimeout(() => clearInterval(pollingInterval), 5000); // Stop polling after success
            } else if (data.status === 'failed') {
                statusDiv.style.color = '#ef4444'; // red
                ingestBtn.disabled = false;
                ingestBtn.style.opacity = '1';
                clearInterval(pollingInterval);
            }

        } catch (e) {
            console.error('Polling error', e);
        }
    }, 2000); // Poll every 2s
}

// Chat Logic
async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    addMessage(text, 'user');
    chatInput.value = '';

    const loading = addTypingIndicator();

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: text, agent_id: currentAgentId })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to get answer');
        }

        const data = await res.json();
        chatHistory.removeChild(loading);
        addMessage(data.answer, 'ai', data.sources);
    } catch (e) {
        chatHistory.removeChild(loading);
        addMessage(`Error: ${e.message}`, 'ai');
    }
}

sendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// --- Folder Browser Logic ---
const browseBtn = document.getElementById('browseBtn');
const browserModal = document.getElementById('browserModal');
const closeBrowserBtn = document.getElementById('closeBrowserBtn');
const folderList = document.getElementById('folderList');
const breadcrumb = document.getElementById('breadcrumb');

let currentBrowseId = 'root';
let pathStack = [{ id: 'root', name: 'root' }];
// Legacy global browser button (removed from HTML) replaced by Agent browser
if (browseBtn) {
    browseBtn.addEventListener('click', () => {
        browserModal.style.display = 'flex';
        loadFolders('root');
    });
}

closeBrowserBtn.addEventListener('click', () => {
    browserModal.style.display = 'none';
});

async function loadFolders(parentId) {
    folderList.innerHTML = '<div style="color: #aaa; text-align: center;">Loading...</div>';
    log(`Browsing: ${parentId}`);

    try {
        const res = await fetch(`/api/browse?parent_id=${encodeURIComponent(parentId)}`);
        if (!res.ok) throw new Error(`Server returned ${res.status}`);

        const data = await res.json();
        console.log("Browse Data:", data);

        if (!data.folders || !Array.isArray(data.folders)) {
            throw new Error("Invalid response format: folders is not an array");
        }

        renderFolders(data.folders);
        updateBreadcrumb();
    } catch (e) {
        console.error(e);
        folderList.innerHTML = `<div style="color: #ef4444; text-align: center;">Error: ${e.message}</div>`;
        log(`Error browsing: ${e.message}`);
    }
}

function renderFolders(folders) {
    folderList.innerHTML = '';

    if (folders.length === 0) {
        folderList.innerHTML = '<div style="color: #aaa; text-align: center;">No subfolders found.</div>';
        return;
    }

    folders.forEach(folder => {
        const div = document.createElement('div');
        div.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 0.8rem; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 0.5rem;';

        div.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem; overflow: hidden;">
                <span style="font-size: 1.2rem;">📁</span>
                <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px;">
                    ${folder.name} <span style="font-size: 0.7em; color: rgba(255,255,255,0.5);">(${folder.id.slice(-6)})</span>
                </span>
            </div>
            <div style="display: flex; gap: 0.5rem;">
                <button class="btn-open" style="background: none; border: 1px solid rgba(255,255,255,0.3); color: white; padding: 0.3rem 0.6rem; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">Open</button>
                <button class="btn-select" style="background: var(--primary-gradient); border: none; color: white; padding: 0.3rem 0.6rem; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">Select</button>
            </div>
        `;

        // Open (Drill down)
        div.querySelector('.btn-open').addEventListener('click', () => {
            currentBrowseId = folder.id;
            pathStack.push({ id: folder.id, name: folder.name });
            loadFolders(folder.id);
        });

        // Select
        div.querySelector('.btn-select').addEventListener('click', () => {
            // Check if we are selecting for Agent Modal or Global/Legacy?
            // We'll set it for the Agent Modal fields since that's the only place we browse now

            if (window.browserTarget === 'agent') {
                agentFolderIdInput.value = folder.id;
                agentFolderDisplayInput.value = folder.name;
            } else {
                // Legacy or other uses
            }

            browserModal.style.display = 'none';
        });

        folderList.appendChild(div);
    });
}

function updateBreadcrumb() {
    breadcrumb.innerHTML = pathStack.map((item, index) => {
        return `<span style="cursor: pointer; text-decoration: underline;" onclick="navigateTo(${index})">${item.name}</span>`;
    }).join(' > ');
}

// Global scope for onclick
window.navigateTo = function (index) {
    pathStack = pathStack.slice(0, index + 1);
    const target = pathStack[pathStack.length - 1];
    currentBrowseId = target.id;
    loadFolders(target.id);
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('App initialized');
    loadAgents();

    // Debug
    console.log('Open Settings Btn:', document.getElementById('openSettingsBtn'));
});
