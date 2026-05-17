/**
 * ZYRABIT SLM CONSOLE
 */

class ZyrabitState {
    constructor() {
        this.backendOnline = false;
        this.modelReady = false;
        this.slmStatus = 'unknown';
        this.messages = [];
        this.ingestTabOpen = false;
        this.isTyping = false;
    }

    updateHealth(data) {
        // Backend returns status: "ok" or "error"
        this.backendOnline = (data.status === 'ok');
        this.slmStatus = data.slm || 'offline';
        this.dbStatus = data.db || 'offline';
        this.modelReady = (this.slmStatus === 'active' || this.slmStatus === 'online');
    }
}

class ZyrabitAPI {
    constructor(timeoutMs = 5000) {
        this.base = window.location.origin;
        this.timeout = timeoutMs;
    }

    /**
     * Standard fetch with Timeout + AbortController
     */
    async _fetch(url, options = {}) {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), this.timeout);

        try {
            const res = await fetch(url, { ...options, signal: controller.signal });
            clearTimeout(id);
            if (!res.ok) {
                const errorData = await res.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${res.status}`);
            }
            return await res.json();
        } catch (e) {
            clearTimeout(id);
            if (e.name === 'AbortError') throw new Error('TIMEOUT_EXCEEDED');
            throw e; // Propagate original error (TypeError for network, etc)
        }
    }

    async getHealth() {
        try {
            return await this._fetch(`${this.base}/health`);
        } catch (e) {
            // No console.error here to keep the dev console clean as requested
            return { api: 'offline', slm: 'offline', model_ready: false, status: 'offline' };
        }
    }

    async getDocuments() {
        return await this._fetch(`${this.base}/v1/documents`);
    }

    async sendChat(payload) {
        return await this._fetch(`${this.base}/v1/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    }

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        try {
            const res = await fetch(`${this.base}/v1/ingest`, {
                method: 'POST',
                body: formData,
                signal: AbortSignal.timeout(30000) // 30s for uploads
            });
            return res.ok;
        } catch (e) {
            return false;
        }
    }

    async runDiagnosis() {
        try {
            const res = await fetch('http://localhost:8001/diagnose', { signal: AbortSignal.timeout(10000) });
            return await res.json();
        } catch (e) {
            throw new Error('DIAGNOSIS_UNREACHABLE');
        }
    }
}

class ZyrabitUI {
    constructor() {
        this.chatContainer = document.getElementById('chat-container');
        this.healthElements = {
            api: document.getElementById('health-api'),
            slm: document.getElementById('health-slm'),
            db: document.getElementById('health-db')
        };
        this.circuitBreaker = document.getElementById('circuit-breaker');
        this.warmupPill = document.getElementById('warmup-pill');
        this.modelBadge = document.getElementById('model-badge');
        this.vaultList = document.getElementById('vault-list');
    }

    renderHealth(state) {
        // Circuit Breaker triggers if API, SLM or DB is down
        const allSystemGo = state.backendOnline && state.slmStatus !== 'offline' && state.dbStatus !== 'offline';
        this.circuitBreaker.classList.toggle('hidden', allSystemGo);

        this.warmupPill.classList.toggle('hidden', state.modelReady);
        this.modelBadge.innerText = `MODEL: ${state.slmStatus.toUpperCase()}`;

        this._updateStatusDot(this.healthElements.api, state.backendOnline ? 'online' : 'offline');
        this._updateStatusDot(this.healthElements.slm, state.slmStatus);
        this._updateStatusDot(this.healthElements.db, state.dbStatus);
    }

    _updateStatusDot(container, status) {
        const dot = container.querySelector('.status-dot');
        const label = container.querySelector('.label');
        dot.className = 'w-2 h-2 rounded-full status-dot transition-all duration-500';
        label.innerText = (status || 'unknown').toUpperCase();

        const colors = {
            online: { dot: 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]', text: 'text-green-600' },
            active: { dot: 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]', text: 'text-green-600' },
            loading: { dot: 'bg-yellow-400 animate-pulse', text: 'text-yellow-600' },
            degraded: { dot: 'bg-yellow-500', text: 'text-yellow-600' },
            offline: { dot: 'bg-red-400', text: 'text-red-500' },
            unknown: { dot: 'bg-gray-300', text: 'text-gray-400' }
        };

        const config = colors[status] || colors.unknown;
        dot.classList.add(...config.dot.split(' '));
        label.className = `text-[10px] font-bold tracking-tight label ${config.text}`;
    }

    renderDocuments(docs) {
        this.vaultList.innerHTML = docs.length === 0
            ? '<p class="text-[10px] text-gray-400 text-center py-8 italic uppercase tracking-widest font-bold">Vault Empty</p>'
            : docs.map(doc => `
                <div class="p-3 bg-zyrabit-surface/40 hover:bg-zyrabit-surface rounded-lg text-[10px] border border-zyrabit-border flex justify-between items-center transition-colors">
                    <span class="font-medium">📄 ${doc.filename}</span>
                    <span class="text-zyrabit-muted">${(doc.size_bytes / 1024).toFixed(1)} KB</span>
                </div>
            `).join('');
    }

    appendMessage(role, content) {
        const msgId = `msg-${Date.now()}`;
        const isUser = role === 'user';
        const isSystem = role === 'system';

        const bubbleClass = isUser
            ? 'bg-zyrabit-primary text-white ml-auto rounded-br-none'
            : isSystem
                ? 'bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-bl-none'
                : 'bg-white border border-zyrabit-border text-zyrabit-text rounded-bl-none shadow-sm';

        const html = `
            <div id="${msgId}" class="flex animate-in fade-in slide-in-from-bottom-2 duration-300">
                <div class="message-bubble p-4 rounded-2xl ${bubbleClass}">
                    ${isSystem ? '<div class="text-[9px] uppercase font-bold text-yellow-600 mb-2 tracking-widest">Security Guard</div>' : ''}
                    <div class="text-sm message-content leading-relaxed">${content}</div>
                    <div class="metadata-area mt-3"></div>
                </div>
            </div>
        `;

        this.chatContainer.insertAdjacentHTML('beforeend', html);
        this.chatContainer.scrollTo({ top: this.chatContainer.scrollHeight, behavior: 'smooth' });
        return msgId;
    }

    updateMessage(id, content, metadata) {
        const msgNode = document.getElementById(id);
        if (!msgNode) return;

        msgNode.querySelector('.message-content').innerText = content;
        if (metadata) {
            msgNode.querySelector('.metadata-area').innerHTML = `
                <div class="flex items-center gap-2 text-[9px] text-zyrabit-muted uppercase font-bold tracking-tighter">
                    <span class="px-1.5 py-0.5 bg-zyrabit-surface rounded border border-zyrabit-border">${metadata.route_decision}</span>
                    <span>${metadata.rag_hits || 0} hits</span>
                    <span class="opacity-50">•</span>
                    <span>${metadata.latency_ms || 0}ms</span>
                </div>
            `;
        }
    }
}

class ZyrabitApp {
    constructor() {
        this.state = new ZyrabitState();
        this.api = new ZyrabitAPI();
        this.ui = new ZyrabitUI();
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.pollHealth();
        this.pollVault();
        const yearEl = document.getElementById('current-year');
        if (yearEl) yearEl.innerText = new Date().getFullYear();
    }

    setupEventListeners() {
        document.getElementById('chat-form').addEventListener('submit', (e) => this.handleChatSubmit(e));

        const textarea = document.getElementById('chat-input');
        textarea.addEventListener('input', () => {
            textarea.style.height = 'auto';
            textarea.style.height = `${textarea.scrollHeight}px`;
        });

        document.getElementById('diagnose-btn').addEventListener('click', () => this.handleDiagnosis());

        // File drop
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => this.handleFileUpload(e.target.files));
    }

    async pollHealth() {
        try {
            const data = await this.api.getHealth();
            this.state.updateHealth(data);
            this.ui.renderHealth(this.state);
        } catch (e) {
            // Quietly update state to offline
            this.state.updateHealth({ api: 'offline', slm: 'offline', model_ready: false });
            this.ui.renderHealth(this.state);
        }
        setTimeout(() => this.pollHealth(), 5000);
    }

    async pollVault() {
        if (this.state.backendOnline) {
            try {
                const data = await this.api.getDocuments();
                this.ui.renderDocuments(data.documents);
            } catch (e) {
                // Secondary check: if vault fails, maybe API is flaking
                console.log("Vault sync paused: Connectivity issue.");
            }
        }
        setTimeout(() => this.pollVault(), 15000);
    }

    async handleChatSubmit(e) {
        e.preventDefault();
        const input = document.getElementById('chat-input');
        const text = input.value.trim();
        if (!text || this.state.isTyping) return;

        this.state.isTyping = true;
        this.ui.appendMessage('user', text);

        // Local PII check feedback
        if (document.getElementById('pii-scrub').checked && /[\w.-]+@[\w.-]+\.[a-z]{2,}/.test(text)) {
            this.ui.appendMessage('system', 'PII detected. Heuristic scrubbing will be applied before inference.');
        }

        const msgId = this.ui.appendMessage('assistant', 'Thinking...');
        input.value = '';
        input.style.height = 'auto';

        try {
            const data = await this.api.sendChat({ text });
            this.ui.updateMessage(msgId, data.response, data.metadata);
        } catch (err) {
            this.ui.updateMessage(msgId, `Processing error: ${err.message}`, { route_decision: 'error' });
        } finally {
            this.state.isTyping = false;
        }
    }

    async handleFileUpload(files) {
        if (!files.length) return;
        this.toggleIngestTab(); // Optional: close or keep open

        for (const file of files) {
            const success = await this.api.uploadFile(file);
            // Quick visual feedback could be improved here but SOLID keeps it in UI
        }
        const data = await this.api.getDocuments();
        this.ui.renderDocuments(data.documents);
    }

    async handleDiagnosis() {
        this.ui.appendMessage('user', 'Run infrastructure MCP diagnosis');
        const msgId = this.ui.appendMessage('assistant', 'Analyzing ports and services...');

        try {
            const data = await this.api.runDiagnosis();
            const response = `Diagnosis: ${data.status}\n\nSuggested action: ${data.suggested_fix}`;
            this.ui.updateMessage(msgId, response, { route_decision: 'mcp-diagnosis' });
        } catch (e) {
            this.ui.updateMessage(msgId, 'Could not contact local MCP server (Port 8001).');
        }
    }

    static toggleIngestTab() {
        const tab = document.getElementById('ingest-tab');
        tab.classList.toggle('hidden');
    }
}

// Global Launcher
window.addEventListener('DOMContentLoaded', () => {
    window.ZyrabitApp = new ZyrabitApp();
});
