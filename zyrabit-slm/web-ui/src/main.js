import { bus } from "./core/EventBus";
import { SocketAdapter } from "./adapters/Socket";
import { ChatManager } from "./services/ChatManager";
import { Renderer } from "./ui/Renderer";
import { EVENTS, IDS } from "./core/Constants";
import { getSafeElement } from "./utils/DOM";
import { Storage } from "./adapters/Storage";


/**
 * Auth Interceptor
 * Automatically injects the local service token into API requests
 */
const originalFetch = window.fetch;
window.fetch = async function(resource, init) {
    init = init || {};
    if (typeof resource === 'string' && resource.startsWith('/v1')) {
        init.headers = {
            ...init.headers,
            'Authorization': 'Bearer zyrabit-local-token'
        };
    }
    return originalFetch(resource, init);
};

/**
 * Zyrabit App Orchestrator
 * Bootstraps the system and wires dependencies.
 */
class ZyrabitApp {
    constructor() {
        this.renderer = new Renderer();
        this.socket = new SocketAdapter();
        this.chat = new ChatManager();
        
        // Recover Conversation memory from Storage
        this.history = Storage.load('chat_history') || []; 
        
        this.init();
    }

    init() {
        this.setupUIListeners();
        this.socket.connect();
        this.startHealthChecks();
        this.checkOnboarding();
        this.chat.recover(); // Recover Shadow State
        
        // Restore visual history
        this.history.forEach(msg => {
            this.renderer.renderMessage(msg.role, msg.content, msg.metadata);
        });
        
        // Hide floating suggestions if history exists
        if (this.chat.queue.length > 0 || this.history.length > 0) {
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
                
                const suggestions = document.getElementById('floating-suggestions');
                if (suggestions) suggestions.style.opacity = '0';
                
                bus.emit(EVENTS.UI.THINKING, true);
                bus.emit(EVENTS.CHAT.SEND, { text, history: this.history });
                this.history.push({ role: 'user', content: text });
                
                Storage.save('chat_history', this.history);
                
                input.value = '';
            };

            // Input focus styling for premium look
            const inputContainer = input.closest('.glass-premium');
            if (inputContainer) {
                input.addEventListener('focus', () => {
                    inputContainer.classList.add('ring-2', 'ring-[#3f5a6d]/20', 'border-[#3f5a6d]/30', 'shadow-3xl');
                    inputContainer.style.transition = 'all 0.3s ease';
                });
                input.addEventListener('blur', () => {
                    inputContainer.classList.remove('ring-2', 'ring-[#3f5a6d]/20', 'border-[#3f5a6d]/30', 'shadow-3xl');
                });
            }

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
        getSafeElement('toggle-settings').onclick = () => this.togglePanel('settings-panel');
        getSafeElement('close-gdpr').onclick = () => this.togglePanel(null);
        getSafeElement('close-ingest').onclick = () => this.togglePanel(null);
        getSafeElement('close-docs').onclick = () => this.togglePanel(null);
        getSafeElement('close-settings').onclick = () => this.togglePanel(null);

        // Telegram modal bindings
        const triggerTelegram = document.getElementById('trigger-telegram');
        const telegramModal = document.getElementById('telegram-modal');
        const closeTelegramModal = document.getElementById('close-telegram-modal');

        if (triggerTelegram && telegramModal) {
            triggerTelegram.onclick = () => {
                telegramModal.classList.remove('hidden');
            };
        }
        if (closeTelegramModal && telegramModal) {
            closeTelegramModal.onclick = () => {
                telegramModal.classList.add('hidden');
            };
        }
        if (telegramModal) {
            telegramModal.onclick = (e) => {
                if (e.target === telegramModal) {
                    telegramModal.classList.add('hidden');
                }
            };
        }

        // 3b. Settings Form Submit
        const settingsForm = document.getElementById('settings-form');
        if (settingsForm) {
            settingsForm.onsubmit = async (e) => {
                e.preventDefault();
                const systemPrompt = getSafeElement('settings-system-prompt').value.trim();
                
                try {
                    const res = await fetch('/v1/profile');
                    if (!res.ok) throw new Error("Could not fetch profile");
                    const profile = await res.json();
                    
                    profile.system_prompt = systemPrompt;
                    
                    const saveRes = await fetch('/v1/profile', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(profile)
                    });
                    if (!saveRes.ok) throw new Error("Save request failed");
                    
                    this.showNotification("System Prompt guardado correctamente", "success");
                    this.togglePanel(null);
                } catch (err) {
                    this.showNotification("Error al guardar prompt", "error");
                }
            };
        }

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

        // 5b. Security Logs (Gatekeeper) & History Update
        bus.on(EVENTS.CHAT.RESPONSE_RECEIVED, (data) => {
            // Update History with Assistant's response
            if (data && data.response) {
                this.history.push({ role: 'assistant', content: data.response, metadata: data.metadata });
                Storage.save('chat_history', this.history);
            }

            if (data && data.metadata && data.metadata.pii_masked && data.metadata.pii_masked.length > 0) {
                data.metadata.pii_masked.forEach(placeholder => {
                    let entityType = "PII";
                    if (placeholder.includes("EMAIL")) entityType = "EMAIL";
                    else if (placeholder.includes("PHONE")) entityType = "PHONE";
                    else if (placeholder.includes("CARD")) entityType = "CREDIT_CARD";
                    else if (placeholder.includes("NAME")) entityType = "NAME";
                    else if (placeholder.includes("IP")) entityType = "IP_ADDRESS";
                    
                    const logMsg = `Filtered ${entityType}: ${placeholder} from query.`;
                    this.addGdprLog("🛡️ GATEKEEPER", logMsg);
                });
            }
        });

        // 6. Gateway Status Notifications
        bus.on(EVENTS.SYSTEM.GATEWAY_CONNECTED, () => {
            this.showNotification("Conexión con el servidor restablecida.", "success");
            try {
                const input = getSafeElement(IDS.CHAT_INPUT);
                const submitBtn = getSafeElement(IDS.CHAT_SUBMIT);
                input.disabled = false;
                submitBtn.disabled = false;
                input.placeholder = "Type your command...";
                
                const statusPill = document.getElementById("status-pill");
                if (statusPill) {
                    statusPill.className = "flex items-center gap-2 px-4 py-2 bg-green-500/10 border border-green-500/20 rounded-full animate-none";
                    const dot = statusPill.querySelector("div");
                    if (dot) dot.className = "w-2 h-2 rounded-full bg-green-500 shadow-sm";
                    const text = statusPill.querySelector("span");
                    if (text) text.textContent = "SYSTEM READY";
                }
            } catch (e) {
                console.warn("⚠️ Failed to update UI elements on gateway connect:", e);
            }
        });
        bus.on(EVENTS.SYSTEM.GATEWAY_DISCONNECTED, (reason) => {
            this.showNotification("Se perdió la conexión con el servidor. Reconectando...", "error");
            try {
                const input = getSafeElement(IDS.CHAT_INPUT);
                const submitBtn = getSafeElement(IDS.CHAT_SUBMIT);
                input.disabled = true;
                submitBtn.disabled = true;
                input.value = '';
                input.placeholder = "Sin conexión con el servidor. Intentando reconectar...";
                
                const statusPill = document.getElementById("status-pill");
                if (statusPill) {
                    statusPill.className = "flex items-center gap-2 px-4 py-2 bg-red-500/10 border border-red-500/20 rounded-full";
                    const dot = statusPill.querySelector("div");
                    if (dot) dot.className = "w-2 h-2 rounded-full bg-red-500 shadow-sm animate-pulse";
                    const text = statusPill.querySelector("span");
                    if (text) text.textContent = "OFFLINE";
                }
            } catch (e) {
                console.warn("⚠️ Failed to update UI elements on gateway disconnect:", e);
            }
        });
    }


    togglePanel(id) {
        if (id === 'settings-panel') {
            this.loadSettings();
        }
        const panels = [IDS.GDPR_PANEL, IDS.INGEST_PANEL, IDS.DOCS_PANEL, 'settings-panel'];
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

    async loadSettings() {
        try {
            const res = await fetch('/v1/profile');
            if (!res.ok) throw new Error("Failed to fetch profile");
            const profile = await res.json();
            const textarea = document.getElementById('settings-system-prompt');
            if (textarea && profile) {
                textarea.value = profile.system_prompt || "";
            }
        } catch (e) {
            console.error("Failed to load settings", e);
        }
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
                    this.socket.connect();
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

        // Show document count in log if it changes
        if (db.metrics?.documents > 0) {
            const count = db.metrics.documents;
            if (this._lastDocCount !== count) {
                this.addGdprLog("VAULT", `Synchronized ${count} documents for context-aware inference.`);
                this._lastDocCount = count;
            }
        }
    }

    async loadVault() {
        try {
            const res = await fetch('/v1/documents');
            if (!res.ok) throw new Error(`HTTP Error: ${res.status}`);
            const data = await res.json();
            const list = document.getElementById('vault-list');
            if (!list) return;
            
            list.innerHTML = '';
            
            if (!data.documents || data.documents.length === 0) {
                list.innerHTML = '<div class="text-xs text-center text-black/40 mt-4">No documents in vault</div>';
                return;
            }
            
            data.documents.forEach(doc => {
                const div = document.createElement('div');
                div.className = 'flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100 group';
                div.innerHTML = `
                    <div class="flex items-center gap-2 overflow-hidden">
                        <span class="text-lg">📄</span>
                        <div class="overflow-hidden">
                            <div class="text-[10px] font-bold truncate doc-name"></div>
                            <div class="text-[8px] opacity-40 doc-size"></div>
                        </div>
                    </div>
                `;
                div.querySelector('.doc-name').textContent = doc.filename;
                div.querySelector('.doc-size').textContent = `${(doc.size_bytes / 1024).toFixed(1)} KB`;
                list.appendChild(div);
            });
        } catch (e) {
            console.error("Failed to load documents:", e);
            const list = document.getElementById('vault-list');
            if (list) {
                list.innerHTML = '<div class="text-xs text-center text-red-500 mt-4">Failed to load documents</div>';
            }
        }
    }

    async loadTools() {
        try {
            const res = await fetch('/v1/tools');
            const data = await res.json();
            const tools = data.tools || [];
            const list = document.getElementById('tools-list');
            if (list) {
                list.innerHTML = '';
                tools.forEach(tool => {
                    const div = document.createElement('div');
                    div.className = 'p-3 bg-white rounded-lg border border-[#a9c4d9]/30 group hover:border-[#3f5a6d] transition shadow-sm';
                    div.innerHTML = `
                        <div class="flex items-center justify-between mb-1">
                            <span class="text-[10px] font-bold text-[#3f5a6d] uppercase tool-name"></span>
                            <span class="text-[8px] px-1 bg-[#e2ecf4] text-[#3f5a6d] rounded">TOOL</span>
                        </div>
                        <p class="text-[9px] text-[#323439]/60 leading-tight tool-desc"></p>
                    `;
                    div.querySelector('.tool-name').textContent = tool.name;
                    div.querySelector('.tool-desc').textContent = tool.description;
                    list.appendChild(div);
                });
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
