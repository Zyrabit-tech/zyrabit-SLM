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
        this.isThinking = false;
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
            this.setThinking(false);
            this.appendMessage('assistant', data.response, data.metadata);
            if (data.metadata?.decision === 'rejected') {
                this.addGdprLog("SECURITY", "QUERY_REJECTED_OUT_OF_SCOPE");
            }
        });
    }

    setThinking(state) {
        this.isThinking = state;
        const input = document.getElementById('chat-input');
        const button = document.querySelector('#chat-form button');
        const container = document.getElementById('chat-container');

        if (state) {
            input.disabled = true;
            input.classList.add('bg-gray-50', 'opacity-50');
            button.disabled = true;
            button.classList.add('opacity-50', 'cursor-not-allowed');
            
            // Add thinking bubble
            const loader = document.createElement('div');
            loader.id = 'thinking-bubble';
            loader.className = 'flex justify-start animate-in fade-in slide-in-from-bottom-2 duration-300';
            loader.innerHTML = `
                <div class="flex items-start gap-3 max-w-[85%]">
                    <div class="w-8 h-8 rounded-full bg-zyrabit-surface border border-zyrabit-border flex items-center justify-center flex-shrink-0">
                        <img src="/img/logo.png" class="w-5 h-5 object-contain animate-pulse">
                    </div>
                    <div class="bg-zyrabit-surface p-4 rounded-2xl rounded-tl-none text-sm text-zyrabit-primary italic flex items-center gap-2">
                        <span class="animate-pulse">Thinking...</span>
                        <div class="flex gap-1">
                            <span class="w-1 h-1 bg-zyrabit-primary rounded-full animate-bounce"></span>
                            <span class="w-1 h-1 bg-zyrabit-primary rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
                            <span class="w-1 h-1 bg-zyrabit-primary rounded-full animate-bounce" style="animation-delay: 0.4s"></span>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(loader);
            container.scrollTop = container.scrollHeight;
        } else {
            input.disabled = false;
            input.classList.remove('bg-gray-50', 'opacity-50');
            button.disabled = false;
            button.classList.remove('opacity-50', 'cursor-not-allowed');
            const loader = document.getElementById('thinking-bubble');
            if (loader) loader.remove();
        }
    }
    async startHealthChecks() {
        const updateHealth = async () => {
            try {
                console.log("Checking health at /v1/health...");
                const res = await fetch('/v1/health');
                if (!res.ok) throw new Error(`HTTP_${res.status}`);
                const data = await res.json();
                console.log("Health data received:", data);
                this.updateUIStatus(data);
            } catch (e) {
                console.error("Health check failed:", e.message);
                this.addGdprLog("SYSTEM", `HEALTH_CHECK_FAILED_${e.message.toUpperCase()}`);
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
        if (!text.trim() || this.isThinking) return;
        this.appendMessage('user', text);
        this.setThinking(true);
        
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
        
        const wrapper = document.createElement('div');
        wrapper.className = `flex items-start gap-3 max-w-[85%] ${role === 'user' ? 'flex-row-reverse' : ''}`;

        // Assistant Avatar
        if (role === 'assistant') {
            const avatar = document.createElement('div');
            avatar.className = 'w-8 h-8 rounded-full bg-zyrabit-surface border border-zyrabit-border flex items-center justify-center flex-shrink-0 mt-1 shadow-sm';
            avatar.innerHTML = `<img src="/img/logo.png" class="w-5 h-5 object-contain">`;
            wrapper.appendChild(avatar);
        }

        const inner = document.createElement('div');
        inner.className = `p-4 rounded-2xl text-sm ${role === 'user' ? 'bg-zyrabit-primary text-white rounded-tr-none' : 'bg-zyrabit-surface text-zyrabit-text border border-zyrabit-border/50 rounded-tl-none'}`;
        inner.innerText = text;

        if (metadata && metadata.latency_ms) {
            const meta = document.createElement('div');
            meta.className = 'text-[9px] mt-2 opacity-50 font-mono flex flex-col gap-1';
            
            let metaHtml = `<span>${metadata.decision.toUpperCase()} | ${metadata.latency_ms}ms | HITS: ${metadata.rag_hits}</span>`;
            
            if (metadata.sources && metadata.sources.length > 0) {
                const uniqueSources = [...new Set(metadata.sources)];
                metaHtml += `<div class="flex flex-wrap gap-1 mt-1">
                    <span class="opacity-70 font-bold">SOURCES:</span>
                    ${uniqueSources.map(s => `<span class="bg-zyrabit-primary/10 px-1 rounded text-[8px] border border-zyrabit-primary/20">${s}</span>`).join('')}
                </div>`;
            }
            
            meta.innerHTML = metaHtml;
            inner.appendChild(meta);
        }

        wrapper.appendChild(inner);
        div.appendChild(wrapper);
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

    showNotification(message, type = 'info') {
        const container = document.getElementById('snackbar-container');
        const card = document.createElement('div');
        card.className = `pointer-events-auto min-w-[200px] p-4 rounded-xl shadow-lg border animate-in slide-in-from-right-10 duration-300 flex items-center gap-3 ${
            type === 'error' ? 'bg-red-50 border-red-200 text-red-800' :
            type === 'warning' ? 'bg-amber-50 border-amber-200 text-amber-800' :
            'bg-white border-zyrabit-border text-zyrabit-primary'
        }`;
        
        const icon = type === 'error' ? '🚫' : type === 'warning' ? '⚠️' : '✅';
        card.innerHTML = `<span class="text-lg">${icon}</span> <div class="text-xs font-bold uppercase tracking-wide">${message}</div>`;
        
        container.appendChild(card);
        setTimeout(() => {
            card.classList.add('animate-out', 'fade-out', 'slide-out-to-right-10');
            setTimeout(() => card.remove(), 300);
        }, 4000);
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
        const content = document.getElementById('drop-zone-content');
        const loader = document.getElementById('drop-zone-loader');
        
        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);
            this.addGdprLog("INGEST", `PROCESSING_${file.name.toUpperCase()}`);
            this.showNotification(`Processing ${file.name}...`, 'info');
            
            // Show loader
            content.classList.add('hidden');
            loader.classList.remove('hidden');

            try {
                const res = await fetch('/v1/ingest', { method: 'POST', body: formData });
                if (!res.ok) throw new Error(`HTTP_${res.status}`);
                
                await this.loadVault();
                this.addGdprLog("INGEST", `SUCCESS_${file.name.toUpperCase()}`);
                this.showNotification(`Successfully ingested ${file.name}`, 'info');
            } catch (e) {
                this.addGdprLog("INGEST", `FAILED_${file.name.toUpperCase()}`);
                this.showNotification(`Failed to ingest ${file.name}: ${e.message}`, 'error');
            } finally {
                // Restore UI
                content.classList.remove('hidden');
                loader.classList.add('hidden');
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.ZyrabitApp = new ZyrabitApp();
});
