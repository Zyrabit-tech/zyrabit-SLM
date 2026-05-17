import { bus } from "./core/EventBus";
import { SocketAdapter } from "./adapters/Socket";
import { ChatManager } from "./services/ChatManager";
import { Renderer } from "./ui/Renderer";
import { EVENTS, IDS } from "./core/Constants";
import { getSafeElement } from "./utils/DOM";


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
        
        // Hide floating suggestions if history exists
        if (this.chat.queue.length > 0) {
            const suggestions = document.getElementById('floating-suggestions');
            if (suggestions) suggestions.style.display = 'none';
        }
        
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
        console.log("🛠️ Initializing UI Listeners (Strict Mode)...");

        // Helper for safe binding
        const bind = (id, event, handler) => {
            try {
                const el = getSafeElement(id);
                el[event] = handler;
            } catch (e) {
                console.warn(`[SKIP] Optional or missing element skipped: #${id}`);
            }
        };

        // 1. Onboarding (Safe because it's a modal)
        const obForm = document.getElementById('onboarding-form');
        if (obForm) {
            obForm.onsubmit = async (e) => {
                e.preventDefault();
                const profile = {
                    name: getSafeElement('ob-name').value,
                    email: getSafeElement('ob-email').value,
                    role: getSafeElement('ob-role').value,
                    interests: getSafeElement('ob-interests').value,
                    persona: getSafeElement('ob-persona').value,
                    tone: getSafeElement('ob-tone').value,
                    assistant_name: getSafeElement('ob-assistant')?.value || 'Zyra',
                    preferred_model: 'qwen2.5:7b'
                };

                
                try {
                    await fetch('/v1/profile', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(profile)
                    });
                    getSafeElement('onboarding-modal').classList.add('hidden');
                    this.showNotification(`System Initialized: Welcome, ${profile.name}`, "success");
                    bus.emit(EVENTS.CHAT.SEND, { 
                        text: `System initialization complete. Identity: ${profile.name}. Role: ${profile.role}. Persona Active: ${profile.persona}. Tone: ${profile.tone}. Await commands.`, 
                        history: [] 
                    });
                } catch (e) {
                    this.showNotification("Error guardando perfil", "error");
                }
            };
            
            const skipBtn = document.getElementById('ob-skip');
            if (skipBtn) skipBtn.onclick = () => getSafeElement('onboarding-modal').classList.add('hidden');
        }

        // 2. Chat Logic (CRITICAL)
        try {
            const form = getSafeElement(IDS.CHAT_FORM);
            const input = getSafeElement(IDS.CHAT_INPUT);

            form.onsubmit = (e) => {
                e.preventDefault();
                const text = input.value.trim();
                if (!text) return;
                
                // Ocultar sugerencias flotantes al iniciar conversación
                const suggestions = document.getElementById('floating-suggestions');
                if (suggestions) suggestions.style.opacity = '0';
                
                bus.emit(EVENTS.UI.THINKING, true);
                bus.emit(EVENTS.CHAT.SEND, { text, history: this.history });
                this.history.push({ role: 'user', content: text });
                input.value = '';
            };



            input.onkeydown = (e) => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    form.requestSubmit();
                }
            };
        } catch (e) {
            console.error("❌ CRITICAL FAILURE: Chat form initialization failed.", e);
        }

        // 3. Navigation & Panels
        bind(IDS.TOGGLE_GDPR, 'onclick', () => this.togglePanel(IDS.GDPR_PANEL));
        getSafeElement('toggle-ingest').onclick = () => this.togglePanel(IDS.INGEST_PANEL);
        getSafeElement('toggle-docs').onclick = () => this.togglePanel(IDS.DOCS_PANEL);
        getSafeElement('close-gdpr').onclick = () => this.togglePanel(null);
        getSafeElement('close-ingest').onclick = () => this.togglePanel(null);
        getSafeElement('close-docs').onclick = () => this.togglePanel(null);

        // 4. File Ingest
        try {
            const dropZone = getSafeElement(IDS.DROP_ZONE);
            const fileInput = getSafeElement(IDS.FILE_INPUT);
            dropZone.onclick = () => fileInput.click();
            fileInput.onchange = (e) => this.handleFileUpload(e.target.files);
        } catch (e) {
            console.warn("⚠️ File ingest UI elements missing. Document upload disabled.");
        }

        // 5. System Logs
        bus.on(EVENTS.SYSTEM.LOG, (data) => this.addGdprLog(data.type, data.event));
    }


    togglePanel(id) {
        const panels = [IDS.GDPR_PANEL, IDS.INGEST_PANEL, IDS.DOCS_PANEL];
        panels.forEach(p => {

            try {
                const el = getSafeElement(p);
                if (p === id) {
                    el.classList.toggle('active');
                } else {
                    el.classList.remove('active');
                }
            } catch (e) {}
        });
    }




    addGdprLog(type, event) {
        try {
            const logs = getSafeElement(IDS.GDPR_LOGS);
            const time = new Date().toLocaleTimeString();
            const div = document.createElement('div');
            div.className = 'border-b border-gray-100 pb-2 mb-2 animate-in slide-in-from-right-4 duration-300';
            
            // Using a safer approach for the inner content
            div.innerHTML = `
                <div class="flex justify-between items-center mb-1">
                    <span class="font-bold text-zyrabit-primary">[${type}]</span>
                    <span class="text-[8px] opacity-40">${time}</span>
                </div>
                <div class="text-gray-600 event-content"></div>
            `;
            div.querySelector('.event-content').textContent = event;
            logs.prepend(div);
        } catch (e) {
            console.warn("Log panel not available yet.");
        }
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
                dot.setAttribute('status', (status || 'OFFLINE').toLowerCase());
            }
        };

        const infra = data.infrastructure || [];
        const db = infra.find(i => i.id === 'vector-db') || { status: 'OFFLINE' };
        const slm = infra.find(i => i.id === 'slm-engine') || { status: 'OFFLINE' };
        const api = infra.find(i => i.id === 'core-api') || { status: 'ONLINE' };
        const mcp = infra.find(i => i.id === 'mcp-bridge') || { status: 'OFFLINE' };

        setStatus('health-api-dot', api.status);
        setStatus('health-slm-dot', slm.status);
        setStatus('health-db-dot', db.status);
        setStatus('health-mcp-dot', mcp.status);


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
        
        const iconSpan = document.createElement('span');
        iconSpan.className = 'snackbar-icon text-xl';
        iconSpan.textContent = icons[type] || 'ℹ️';

        const content = document.createElement('div');
        content.className = 'flex-1';

        const typeLabel = document.createElement('div');
        typeLabel.className = 'snackbar-label text-[10px] font-bold uppercase tracking-wider';
        typeLabel.textContent = type;

        const messageLabel = document.createElement('div');
        messageLabel.className = 'text-xs text-black/70 font-medium';
        messageLabel.textContent = message;

        content.appendChild(typeLabel);
        content.appendChild(messageLabel);
        el.appendChild(iconSpan);
        el.appendChild(content);

        container.appendChild(el);

        // Auto-remove
        setTimeout(() => {
            el.classList.replace('snackbar-enter', 'snackbar-exit');
            setTimeout(() => el.remove(), 500);
        }, 5000);

    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ZyrabitApp();
});
