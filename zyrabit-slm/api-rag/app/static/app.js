// --- CONFIGURATION ---
const API_BASE = window.location.origin;
const HEALTH_URL = `${API_BASE}/health`;
const CHAT_URL = `${API_BASE}/v1/chat`;
const INGEST_URL = `${API_BASE}/v1/ingest`;
const DOCUMENTS_URL = `${API_BASE}/v1/documents`;

let state = {
    backendOnline: false,
    modelReady: false,
    slmStatus: 'unknown',
    messages: [],
    ingestTabOpen: false
};

// --- UI HELPERS ---
const $ = (id) => document.getElementById(id);

function toggleIngestTab() {
    state.ingestTabOpen = !state.ingestTabOpen;
    $('ingest-tab').classList.toggle('hidden', !state.ingestTabOpen);
    if(state.ingestTabOpen) fetchVaultDocs();
}

function updateHealthUI(health) {
    state.backendOnline = health.api === 'online';
    state.modelReady = health.model_ready;
    state.slmStatus = health.slm;

    // Circuit Breaker Logic
    $('circuit-breaker').classList.toggle('hidden', state.backendOnline);

    // Sidebar status dots
    const apiDot = $('health-api').querySelector('.status-dot');
    const slmDot = $('health-slm').querySelector('.status-dot');
    const dbDot = $('health-db').querySelector('.status-dot');
    
    updateIndicator(apiDot, $('health-api').querySelector('.label'), health.api);
    updateIndicator(slmDot, $('health-slm').querySelector('.label'), health.slm);
    updateIndicator(dbDot, $('health-db').querySelector('.label'), 'online'); // Assuming backend check handles this

    // Warm-up logic
    $('warmup-pill').classList.toggle('hidden', state.modelReady);
    $('model-badge').innerText = `MODEL: ${health.slm.toUpperCase()}`;
}

function updateIndicator(dot, label, status) {
    dot.className = 'w-2 h-2 rounded-full status-dot';
    label.innerText = status.toUpperCase();
    if (status === 'online') {
        dot.classList.add('bg-green-500', 'shadow-[0_0_8px_#22c55e]');
        label.className = 'text-xs font-bold text-green-500 label';
    } else if (status === 'degraded' || status === 'loading') {
        dot.classList.add('bg-yellow-500', 'shadow-[0_0_8px_#eab308]');
        label.className = 'text-xs font-bold text-yellow-500 label';
    } else {
        dot.classList.add('bg-red-500', 'shadow-[0_0_8px_#ef4444]');
        label.className = 'text-xs font-bold text-red-500 label';
    }
}

// --- API ACTIONS ---
async function checkHealth() {
    try {
        const res = await fetch(HEALTH_URL);
        const data = await res.json();
        updateHealthUI(data);
    } catch (err) {
        updateHealthUI({ api: 'offline', slm: 'offline', model_ready: false });
    }
}

async function fetchVaultDocs() {
    try {
        const res = await fetch(DOCUMENTS_URL);
        const data = await res.json();
        const list = $('vault-list');
        list.innerHTML = '';
        if (data.documents.length === 0) {
            list.innerHTML = '<p class="text-[10px] text-gray-500 text-center py-4 italic">El baúl está vacío</p>';
            return;
        }
        data.documents.forEach(doc => {
            const kb = (doc.size_bytes / 1024).toFixed(1);
            const div = document.createElement('div');
            div.className = 'p-3 bg-hardgray-700/50 rounded-lg text-[10px] border border-hardgray-600 flex justify-between items-center';
            div.innerHTML = `<span>📄 ${doc.filename}</span> <span class="text-gray-500">${kb} KB</span>`;
            list.appendChild(div);
        });
    } catch (err) {
        console.error("Vault fetch failed", err);
    }
}

async function sendMessage(text) {
    // 1. Add User Message to UI
    appendMessage('user', text);
    
    // 2. Prepare payload
    const payload = { text: text };
    
    // 3. Simple Client-side PII warning (visual only)
    if ($('pii-scrub').checked && /[\w.-]+@[\w.-]+\.[a-z]{2,}/.test(text)) {
        appendMessage('system', '⚠️ Detectaste PII (Email). El sistema enmascarará este dato antes de la inferencia.');
    }

    const assistantMsgId = appendMessage('assistant', '...', true);
    
    try {
        const res = await fetch(CHAT_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        const data = await res.json();
        updateAssistantMessage(assistantMsgId, data.response, data.metadata);
    } catch (err) {
        updateAssistantMessage(assistantMsgId, `🚫 Error: ${err.message}`, { route_decision: 'error' });
    }
}

// --- DOM LOGIC ---
function appendMessage(role, content, isLoading = false) {
    const container = $('chat-container');
    const msgId = Date.now();
    const div = document.createElement('div');
    div.id = `msg-${msgId}`;
    div.className = `flex ${role === 'user' ? 'justify-end' : 'justify-start'}`;
    
    const innerHtml = `
        <div class="message-bubble p-4 rounded-2xl ${role === 'user' ? 'bg-zyrabit-primary text-white rounded-tr-none' : 'bg-hardgray-800 border border-hardgray-700 rounded-tl-none'}">
            ${role === 'system' ? '<div class="text-[10px] uppercase font-bold text-yellow-500 mb-2">System Guard</div>' : ''}
            <div class="text-sm message-content leading-relaxed">${content}</div>
            <div class="mt-2 metadata-area"></div>
        </div>
    `;
    div.innerHTML = innerHtml;
    container.appendChild(div);
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
    return msgId;
}

function updateAssistantMessage(id, content, metadata) {
    const msg = $(`msg-${id}`);
    if (!msg) return;
    msg.querySelector('.message-content').innerText = content;
    
    if (metadata) {
        const metaArea = msg.querySelector('.metadata-area');
        metaArea.innerHTML = `
            <div class="flex items-center gap-2 mt-4 text-[9px] text-gray-500 uppercase font-bold">
                <span class="px-2 py-0.5 bg-hardgray-900 rounded border border-hardgray-600">${metadata.route_decision}</span>
                <span>${metadata.rag_hits || 0} hits</span>
                <span>${metadata.latency_ms || 0}ms</span>
            </div>
        `;
    }
}

// --- EVENT LISTENERS ---
$('chat-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const input = $('chat-input');
    const text = input.value.trim();
    if (!text) return;
    sendMessage(text);
    input.value = '';
    input.style.height = 'auto';
});

// Auto-resize textarea
$('chat-input').addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

// File Ingestion Logic
$('drop-zone').addEventListener('click', () => $('file-input').click());
$('file-input').addEventListener('change', async (e) => {
    const files = e.target.files;
    if (files.length === 0) return;
    
    for (let file of files) {
        const formData = new FormData();
        formData.append('file', file);
        
        // Show temporary status in vault
        const list = $('vault-list');
        const statusItem = document.createElement('div');
        statusItem.className = 'p-3 bg-blue-900/20 border border-blue-500/30 rounded-lg text-[10px] animate-pulse';
        statusItem.innerText = `Subiendo: ${file.name}...`;
        list.prepend(statusItem);

        try {
            const res = await fetch(INGEST_URL, {
                method: 'POST',
                body: formData
            });
            if (res.ok) {
                statusItem.className = 'p-3 bg-green-900/20 border border-green-500/30 rounded-lg text-[10px]';
                statusItem.innerText = `✅ Éxito: ${file.name}`;
            } else {
                statusItem.className = 'p-3 bg-red-900/20 border border-red-500/30 rounded-lg text-[10px]';
                statusItem.innerText = `❌ Error: ${file.name}`;
            }
        } catch (err) {
            statusItem.innerText = `❌ Error Conexión: ${file.name}`;
        }
    }
    setTimeout(fetchVaultDocs, 2000);
});

// --- INITIALIZATION ---
checkHealth();
setInterval(checkHealth, 5000);
setInterval(fetchVaultDocs, 15000);

// Diagnose button (Simple integration)
$('diagnose-btn').addEventListener('click', async () => {
    appendMessage('user', 'Iniciando diagnóstico MCP...');
    const assistantMsgId = appendMessage('assistant', 'Analizando infraestructura...', true);
    
    try {
        const res = await fetch('http://localhost:8001/diagnose', { timeout: 15000 });
        if (res.ok) {
            const data = await res.json();
            const diagMsg = `**Diagnóstico detectado:**\n${data.status}\n\n**Sugerencia:** ${data.suggested_fix}`;
            updateAssistantMessage(assistantMsgId, diagMsg, { route_decision: 'mcp-diagnostic' });
        } else {
            updateAssistantMessage(assistantMsgId, 'Error al contactar con el servidor MCP.');
        }
    } catch (err) {
        updateAssistantMessage(assistantMsgId, 'El servidor MCP no responde. ¿Está corriendo el contenedor mcp-server?');
    }
});
