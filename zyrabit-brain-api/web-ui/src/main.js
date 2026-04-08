import { io } from "socket.io-client";

/**
 * Zyrabit SLM Console - Main Controller (Application Layer)
 * Implements a mini-hexagonal architecture:
 * - Domain: Chat logic, message formatting.
 * - Adapters: Socket.io for real-time, Fetch for HTTP, DOM for UI.
 */

class ZyrabitApp {
    constructor() {
        this.socket = null;
        this.piiGuardEnabled = true;
        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.connectSocket();
        this.startHealthChecks();
        this.loadVault();
    }

    setupEventListeners() {
        // UI Interaction
        document.getElementById('toggle-gdpr').onclick = () => this.togglePanel('gdpr-panel');
        document.getElementById('close-gdpr').onclick = () => this.togglePanel('gdpr-panel');
        document.getElementById('toggle-ingest').onclick = () => this.togglePanel('ingest-panel');
        document.getElementById('close-ingest').onclick = () => this.togglePanel('ingest-panel');

        // Chat Form
        const form = document.getElementById('chat-form');
        const input = document.getElementById('chat-input');
        form.onsubmit = (e) => {
            e.preventDefault();
            this.sendMessage(input.value);
            input.value = '';
        };

        // File Ingest
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        dropZone.onclick = () => fileInput.click();
        fileInput.onchange = (e) => this.handleFileUpload(e.target.files);
    }

    connectSocket() {
        // In local bridge, we use same host
        const socketUrl = window.location.origin;
        this.socket = io(socketUrl, { path: "/socket.io" });

        this.socket.on("connect", () => {
            console.log("Connected to Zyrabit Sovereign Gateway");
            this.addGdprLog("SYSTEM", "SECURE_GATEWAY_ESTABLISHED");
        });

        this.socket.on("chat_response", (data) => {
            this.appendMessage('assistant', data.response, data.metadata);
            if (data.metadata?.decision === 'rejected') {
                this.addGdprLog("SECURITY", "QUERY_REJECTED_OUT_OF_SCOPE");
            }
        });
    }

    async startHealthChecks() {
        const updateHealth = async () => {
            try {
                const res = await fetch('/health');
                const data = await res.json();
                this.updateUIStatus(data);
            } catch (e) {
                console.error("Health check failed");
            }
        };
        updateHealth();
        setInterval(updateHealth, 10000);
    }

    updateUIStatus(data) {
        const setStatus = (id, status) => {
            const el = document.getElementById(id);
            const dot = el.querySelector('.status-dot');
            const label = el.querySelector('.label');
            if (status === 'online') {
                dot.className = 'w-2 h-2 rounded-full bg-green-500 shadow-sm';
                label.innerText = 'ONLINE';
                label.className = 'text-[10px] font-bold text-green-600 label';
            } else {
                dot.className = 'w-2 h-2 rounded-full bg-red-500 shadow-sm';
                label.innerText = 'OFFLINE';
                label.className = 'text-[10px] font-bold text-red-600 label';
            }
        };

        setStatus('health-api', 'online'); // If we reached this, API is online
        setStatus('health-slm', data.slm);
        setStatus('health-db', data.db);

        const modelBadge = document.getElementById('model-badge');
        modelBadge.innerText = `MODEL: ${data.model || '...'}`;
        
        const pill = document.getElementById('status-pill');
        if (data.slm === 'online') {
            pill.classList.remove('hidden');
        } else {
            pill.classList.add('hidden');
        }
    }

    sendMessage(text) {
        if (!text.trim()) return;
        this.appendMessage('user', text);
        
        // GDPR Pre-processing Log
        if (document.getElementById('pii-scrub').checked) {
            this.addGdprLog("PRIVACY", "PII_SCAN_INITIATED");
            // Here we could simulate localized scrubbing logs
            if (text.match(/\d{4}-\d{4}/)) { // Simple mask
                this.addGdprLog("SECURITY", "ENTITY_REDACTED_MOCKED");
            }
        }

        this.socket.emit("chat_message", { text });
    }

    appendMessage(role, text, metadata = null) {
        const container = document.getElementById('chat-container');
        const div = document.createElement('div');
        div.className = `flex ${role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-4 duration-300`;
        
        const inner = document.createElement('div');
        inner.className = `max-w-[85%] p-4 rounded-2xl text-sm ${role === 'user' ? 'bg-zyrabit-primary text-white' : 'bg-zyrabit-surface text-zyrabit-text border border-zyrabit-border/50'}`;
        inner.innerText = text;

        if (metadata && metadata.latency_ms) {
            const meta = document.createElement('div');
            meta.className = 'text-[9px] mt-2 opacity-50 font-mono';
            meta.innerText = `${metadata.decision.toUpperCase()} | ${metadata.latency_ms}ms | HITS: ${metadata.rag_hits}`;
            inner.appendChild(meta);
        }

        div.appendChild(inner);
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    togglePanel(id) {
        const panels = ['gdpr-panel', 'ingest-panel'];
        panels.forEach(p => {
            const el = document.getElementById(p);
            if (p === id) {
                el.classList.toggle('translate-x-full');
            } else {
                el.classList.add('translate-x-full');
            }
        });
    }

    addGdprLog(type, event) {
        const logs = document.getElementById('gdpr-logs');
        const time = new Date().toLocaleTimeString();
        const div = document.createElement('div');
        div.className = 'border-b border-gray-100 pb-2 mb-2 animate-in slide-in-from-right-4 duration-300';
        div.innerHTML = `
            <div class="flex justify-between items-center mb-1">
                <span class="font-bold text-zyrabit-primary">[${type}]</span>
                <span class="text-[8px] opacity-40">${time}</span>
            </div>
            <div class="text-gray-600">${event}</div>
        `;
        logs.prepend(div);
    }

    async loadVault() {
        try {
            const res = await fetch('/v1/documents');
            const data = await res.json();
            const list = document.getElementById('vault-list');
            list.innerHTML = data.documents.map(doc => `
                <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100 group">
                    <div class="flex items-center gap-2 overflow-hidden">
                        <span class="text-lg">📄</span>
                        <div class="overflow-hidden">
                            <div class="text-[10px] font-bold truncate">${doc.filename}</div>
                            <div class="text-[8px] opacity-40">${(doc.size_bytes / 1024).toFixed(1)} KB</div>
                        </div>
                    </div>
                </div>
            `).join('');
        } catch (e) {
            console.error("Failed to load vault");
        }
    }

    async handleFileUpload(files) {
        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);
            this.addGdprLog("INGEST", `PROCESSING_${file.name.toUpperCase()}`);
            try {
                await fetch('/v1/ingest', { method: 'POST', body: formData });
                this.loadVault();
                this.addGdprLog("INGEST", `SUCCESS_${file.name.toUpperCase()}`);
            } catch (e) {
                this.addGdprLog("INGEST", `FAILED_${file.name.toUpperCase()}`);
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.ZyrabitApp = new ZyrabitApp();
});
