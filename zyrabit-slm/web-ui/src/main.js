import { bus } from "./core/EventBus";
import { SocketAdapter } from "./adapters/Socket";
import { ChatManager } from "./services/ChatManager";
import { Renderer } from "./ui/Renderer";

/**
 * Zyrabit App Orchestrator
 * Bootstraps the system and wires dependencies.
 */
class ZyrabitApp {
    constructor() {
        this.renderer = new Renderer();
        this.socket = new SocketAdapter();
        this.chat = new ChatManager();
        this.history = []; // Conversation memory
        
        this.init();
    }

    init() {
        this.setupUIListeners();
        this.socket.connect();
        this.startHealthChecks();
        this.checkOnboarding();
        this.chat.recover(); // Recover Shadow State
        this.loadVault();
        this.loadTools();
    }

    async checkOnboarding() {
        try {
            const res = await fetch('/v1/profile');
            const profile = await res.json();
            
            if (!profile || !profile.onboarding_completed) {
                document.getElementById('onboarding-modal').classList.remove('hidden');
            }
        } catch (e) {
            console.error("Profile check failed", e);
        }
    }

    setupUIListeners() {
        // Onboarding Form
        const obForm = document.getElementById('onboarding-form');
        if (obForm) {
            obForm.onsubmit = async (e) => {
                e.preventDefault();
                const profile = {
                    name: document.getElementById('ob-name').value,
                    email: document.getElementById('ob-email').value,
                    role: document.getElementById('ob-role').value,
                    interests: document.getElementById('ob-interests').value,
                    persona: document.getElementById('ob-persona').value,
                    tone: document.getElementById('ob-tone').value,
                    preferred_model: 'qwen2.5:7b' // Default for now, can be expanded
                };
                
                try {
                    await fetch('/v1/profile', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(profile)
                    });
                    document.getElementById('onboarding-modal').classList.add('hidden');
                    this.showNotification(`System Initialized: Welcome, ${profile.name}`, "success");
                    // Send a welcoming message from Zyra in the chosen persona tone
                    bus.emit('CHAT:SEND', { 
                        text: `System initialization complete. Identity: ${profile.name}. Role: ${profile.role}. Persona Active: ${profile.persona}. Tone: ${profile.tone}. Await commands.`, 
                        history: [] 
                    });

                } catch (e) {
                    this.showNotification("Error guardando perfil", "error");
                }
            };
            
            document.getElementById('ob-skip').onclick = () => {
                document.getElementById('onboarding-modal').classList.add('hidden');
            };
        }
        // Chat Form
        const form = document.getElementById('chat-form');
        const input = document.getElementById('chat-input');
        form.onsubmit = (e) => {
            e.preventDefault();
            if (!input.value.trim()) return;
            const text = input.value;
            bus.emit('CHAT:SEND', { text, history: this.history });
            this.history.push({ role: 'user', content: text });
            input.value = '';
        };

        // Keyboard Shortcuts (Cmd+Enter or Ctrl+Enter)
        input.onkeydown = (e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                form.requestSubmit(); // Triggers form.onsubmit
            }
        };

        // UI Interaction
        document.getElementById('toggle-gdpr').onclick = () => this.togglePanel('gdpr-panel');
        document.getElementById('close-gdpr').onclick = () => this.togglePanel('gdpr-panel');
        document.getElementById('toggle-ingest').onclick = () => this.togglePanel('ingest-panel');
        document.getElementById('close-ingest').onclick = () => this.togglePanel('ingest-panel');

        // File Ingest
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        dropZone.onclick = () => fileInput.click();
        fileInput.onchange = (e) => this.handleFileUpload(e.target.files);

        // System Logs
        bus.on('SYSTEM:LOG', (data) => this.addGdprLog(data.type, data.event));
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

    async startHealthChecks() {
        let isOffline = false;
        const updateHealth = async () => {
            try {
                const res = await fetch('/v1/health');
                if (!res.ok) throw new Error(`HTTP_${res.status}`);
                const data = await res.json();
                this.updateUIStatus(data);
                
                if (isOffline) {
                    this.showNotification("Connection Restored", "success");
                    isOffline = false;
                }
            } catch (e) {
                this.addGdprLog("SYSTEM", `HEALTH_CHECK_FAILED`);
                if (!isOffline) {
                    this.showNotification("Connection Lost: API Offline", "error");
                    isOffline = true;
                }
            }
        };
        updateHealth();
        setInterval(updateHealth, 10000);
    }

    updateUIStatus(data) {
        const setStatus = (dotId, status) => {
            const dot = document.getElementById(dotId);
            if (dot) {
                dot.setAttribute('status', status.toLowerCase());
            }
        };


        // Parse infrastructure array
        const infra = data.infrastructure || [];
        const db = infra.find(i => i.id === 'vector-db') || { status: 'OFFLINE' };
        const slm = infra.find(i => i.id === 'slm-engine') || { status: 'OFFLINE' };
        const api = infra.find(i => i.id === 'core-api') || { status: 'ONLINE' };

        setStatus('health-api-dot', api.status);
        setStatus('health-slm-dot', slm.status);
        setStatus('health-db-dot', db.status);

        // Update SLM Mode Label
        const modeLabel = document.getElementById('slm-mode-label');
        if (modeLabel) {
            modeLabel.innerText = slm.mode || '';
        }

        // Update Model Badge
        const modelBadge = document.getElementById('model-badge');
        if (modelBadge) {
            const modelName = slm.name ? slm.name.split('(')[1]?.replace(')', '') : '...';
            modelBadge.innerText = `MODEL: ${modelName || '...'}`;
        }
        
        // Detailed log if DB or SLM are offline (only log once per state change ideally, but here simple is fine)
        if (db.status === 'OFFLINE') {
            this.addGdprLog("SYSTEM", "VECTOR_DB_DISCONNECTED - Check zyrabit-db container");
        }
        if (slm.status === 'OFFLINE' && slm.mode === 'Local Host (Mac)') {
            this.addGdprLog("SYSTEM", "LOCAL_OLLAMA_OFFLINE - Make sure Ollama app is open on your Mac");
        }

        // Show document count in log if it changes (simple check)
        if (db.metrics?.documents > 0) {
            const count = db.metrics.documents;
            if (this._lastDocCount !== count) {
                this.addGdprLog("VAULT", `SYNCED_${count}_DOCUMENTS`);
                this._lastDocCount = count;
            }
        }
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
        } catch (e) {}
    }

    async loadTools() {
        try {
            const res = await fetch('/v1/tools');
            const data = await res.json();
            const tools = data.tools || [];
            const list = document.getElementById('tools-list');
            if (list) {
                list.innerHTML = tools.map(tool => `
                    <div class="p-3 bg-white rounded-lg border border-[#a9c4d9]/30 group hover:border-[#3f5a6d] transition shadow-sm">
                        <div class="flex items-center justify-between mb-1">
                            <span class="text-[10px] font-bold text-[#3f5a6d] uppercase">${tool.name}</span>
                            <span class="text-[8px] px-1 bg-[#e2ecf4] text-[#3f5a6d] rounded">TOOL</span>
                        </div>
                        <p class="text-[9px] text-[#323439]/60 leading-tight">${tool.description}</p>
                    </div>
                `).join('');
            }
        } catch (e) {
            console.error("Failed to load tools", e);
        }
    }

    async handleFileUpload(files) {
        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);
            this.addGdprLog("INGEST", `PROCESSING_${file.name.toUpperCase()}`);
            
            // UI Feedback: Loading
            const dropZone = document.getElementById('drop-zone-content');
            const loader = document.getElementById('drop-zone-loader');
            if (dropZone && loader) {
                dropZone.classList.add('hidden');
                loader.classList.remove('hidden');
            }

            try {
                const res = await fetch('/v1/ingest', { method: 'POST', body: formData });
                if (!res.ok) throw new Error(`HTTP_${res.status}`);
                await this.loadVault();
                this.addGdprLog("INGEST", `SUCCESS_${file.name.toUpperCase()}`);
                this.showNotification(`File uploaded: ${file.name}`, "success");
            } catch (e) {
                this.addGdprLog("INGEST", `FAILED_${file.name.toUpperCase()}`);
                this.showNotification(`Upload failed: ${file.name}`, "error");
            } finally {
                const dropZone = document.getElementById('drop-zone-content');
                const loader = document.getElementById('drop-zone-loader');
                if (dropZone && loader) {
                    dropZone.classList.remove('hidden');
                    loader.classList.add('hidden');
                }
            }
        }
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('snackbar-container');
        if (!container) return;

        const el = document.createElement('div');
        const icons = {
            success: '✅',
            error: '❌',
            info: 'ℹ️'
        };

        el.className = `snackbar snackbar-${type} snackbar-enter`;
        el.innerHTML = `
            <span class="text-lg">${icons[type]}</span>
            <div class="flex-1">
                <div class="text-[10px] font-bold uppercase tracking-wider">${type}</div>
                <div class="text-xs opacity-90">${message}</div>
            </div>
        `;

        container.appendChild(el);

        // Animation: Enter
        requestAnimationFrame(() => {
            el.classList.remove('snackbar-enter');
        });

        // Auto-remove
        setTimeout(() => {
            el.classList.add('snackbar-exit');
            el.addEventListener('transitionend', () => el.remove());
        }, 5000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ZyrabitApp();
});
