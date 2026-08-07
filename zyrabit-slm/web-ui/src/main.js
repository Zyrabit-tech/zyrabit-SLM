import { bus } from "./core/EventBus";
import { SocketAdapter } from "./adapters/Socket";
import { ChatManager } from "./services/ChatManager";
import { Renderer } from "./ui/Renderer";
import { EVENTS, IDS } from "./core/Constants";
import { getSafeElement } from "./utils/DOM";
import { Storage } from "./adapters/Storage";


/**
 * Auth Interceptor
 * Injects the token provided to the local container at startup.
 */
const originalFetch = window.fetch;
window.fetch = async function (resource, init) {
    init = init || {};
    if (typeof resource === 'string' && resource.startsWith('/v1')) {
        init.headers = {
            ...init.headers,
            'Authorization': `Bearer ${window.ZYRABIT_RUNTIME_CONFIG?.apiToken || ''}`
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
        this.checkOnboarding();

        const shell = document.getElementById('app-shell');
        const collapse = document.getElementById('collapse-library');
        const open = document.getElementById('open-library');
        if (shell && Storage.load('library_collapsed')) shell.classList.add('library-collapsed');
        if (collapse && shell) collapse.onclick = () => {
            shell.classList.toggle('library-collapsed');
            Storage.save('library_collapsed', shell.classList.contains('library-collapsed'));
        };
        if (open && shell) open.onclick = () => shell.classList.toggle('library-open');
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
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    form.requestSubmit();
                }
            };
        } catch (e) {
            console.error("❌ CRITICAL FAILURE: Chat form initialization failed.", e);
        }

        // 3. Navigation & Panels
        bind(IDS.TOGGLE_GDPR, 'onclick', () => this.togglePanel(IDS.GDPR_PANEL));
        getSafeElement('toggle-ingest').onclick = () => getSafeElement(IDS.FILE_INPUT).click();
        getSafeElement('toggle-docs').onclick = () => this.togglePanel(IDS.DOCS_PANEL);
        bind('clear-conversation', 'onclick', () => {
            this.history = [];
            Storage.remove('chat_history');
            Storage.remove('pending_messages');
            this.chat.resetSession();
            bus.emit('UI:CLEAR_CHAT');
            this.showNotification('Conversation cleared.', 'success');
        });
        getSafeElement('toggle-settings').onclick = () => this.togglePanel('settings-panel');
        getSafeElement('close-gdpr').onclick = () => this.togglePanel(null);
        bind('close-ingest', 'onclick', () => this.togglePanel(null));
        getSafeElement('close-docs').onclick = () => this.togglePanel(null);
        getSafeElement('close-settings').onclick = () => this.togglePanel(null);

        document.querySelectorAll('.prompt-chip, .starter[data-prompt]').forEach((button) => {
            button.onclick = () => {
                const input = getSafeElement(IDS.CHAT_INPUT);
                input.value = button.dataset.prompt || '';
                input.focus();
            };
        });

        const clearSources = document.getElementById('clear-sources');
        if (clearSources) clearSources.onclick = () => this.renderSources([]);
        window.addEventListener('zyra:sources', (event) => this.renderSources(event.detail || []));

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
                input.placeholder = "Ask about your documents…";

                const statusPill = document.getElementById("status-pill");
                if (statusPill) {
                    statusPill.className = "connection-status connected";
                    const dot = statusPill.querySelector("i");
                    if (dot) dot.className = "w-2 h-2 rounded-full bg-green-500 shadow-sm";
                    const text = statusPill.querySelector("span");
                    if (text) text.textContent = "Local workspace";
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
                    statusPill.className = "connection-status disconnected";
                    const dot = statusPill.querySelector("i");
                    if (dot) dot.className = "w-2 h-2 rounded-full bg-red-500 shadow-sm animate-pulse";
                    const text = statusPill.querySelector("span");
                    if (text) text.textContent = "Reconnecting";
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
            } catch (e) { }
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
            div.className = 'activity-event';

            // Using a safer approach for the inner content
            div.innerHTML = `
                <div class="activity-event-head">
                    <span>${type}</span>
                    <time>${time}</time>
                </div>
                <div class="event-content"></div>
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

            const count = document.getElementById('document-count');
            if (count) count.textContent = String(data.documents?.length || 0);

            if (!data.documents || data.documents.length === 0) {
                list.innerHTML = '<div class="empty-library">No documents yet. Import one to start asking questions.</div>';
                return;
            }

            data.documents.forEach(doc => {
                const div = document.createElement('button');
                div.type = 'button';
                div.className = 'document-row';
                div.innerHTML = `
                    <span class="document-glyph">⌑</span>
                    <div class="overflow-hidden">
                        <div class="document-name"></div>
                        <div class="document-size"></div>
                        </div>
                `;
                div.querySelector('.document-name').textContent = doc.filename;
                div.querySelector('.document-size').textContent = `${(doc.size_bytes / 1024).toFixed(1)} KB`;
                div.onclick = () => this.selectDocument(doc, div);
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

    selectDocument(doc, row) {
        const filename = doc.filename;
        document.querySelectorAll('.document-row.active').forEach((item) => item.classList.remove('active'));
        row.classList.add('active');
        const title = document.getElementById('active-document-title');
        const description = document.getElementById('active-document-description');
        if (title) title.textContent = filename;
        if (description) description.textContent = 'Ask a question about this document or compare it with the rest of your library.';
        this.setActiveDocument(filename, doc.id);
        const input = document.getElementById(IDS.CHAT_INPUT);
        if (input) {
            input.placeholder = `Ask about ${filename}…`;
            input.focus();
        }
    }

    setActiveDocument(filename, documentId = null) {
        const chip = document.getElementById('active-context-chip');
        const name = document.getElementById('active-context-name');
        if (!chip || !name) return;
        if (!filename) {
            chip.classList.add('hidden');
            delete chip.dataset.documentId;
            return;
        }
        name.textContent = filename;
        if (documentId) chip.dataset.documentId = documentId;
        chip.classList.remove('hidden');
        const clear = document.getElementById('clear-active-document');
        if (clear) clear.onclick = () => this.clearActiveDocument();
    }

    clearActiveDocument() {
        document.querySelectorAll('.document-row.active').forEach((item) => item.classList.remove('active'));
        const title = document.getElementById('active-document-title');
        const description = document.getElementById('active-document-description');
        if (title) title.textContent = 'All documents';
        if (description) description.textContent = 'Your local workspace';
        this.setActiveDocument(null);
        const input = document.getElementById(IDS.CHAT_INPUT);
        if (input) input.placeholder = 'Ask about your documents…';
    }

    renderSources(sources) {
        const list = document.getElementById('sources-list');
        if (!list) return;
        list.innerHTML = '';
        const uniqueSources = sources || [];
        if (uniqueSources.length === 0) {
            list.innerHTML = '<div class="context-empty"><span aria-hidden="true">⌁</span><p>Sources used in an answer will appear here.</p></div>';
            return;
        }
        uniqueSources.forEach((source) => {
            const card = document.createElement('div');
            card.className = 'source-card';
            const name = document.createElement('strong');
            name.textContent = typeof source === 'string' ? source : source.filename;
            const note = document.createElement('span');
            if (typeof source === 'string') note.textContent = 'Used as answer context';
            else {
                const locator = source.locator || {};
                const location = locator.page ? `Page ${locator.page}` : locator.sheet ? `${locator.sheet} ${locator.range || ''}` : locator.slide ? `Slide ${locator.slide}` : 'Document evidence';
                note.textContent = source.excerpt ? `${location} · ${source.excerpt}` : location;
            }
            card.append(name, note);
            list.appendChild(card);
        });
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
                const accepted = await res.json();
                if (accepted.job_id) await this.waitForJob(accepted.job_id);
                await this.loadVault();
                const title = document.getElementById('active-document-title');
                const description = document.getElementById('active-document-description');
                if (title) title.textContent = file.name;
                if (description) description.textContent = 'Indexed and ready for questions.';
                this.setActiveDocument(file.name, accepted.document_id);
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

    async waitForJob(jobId) {
        const deadline = Date.now() + 120000;
        while (Date.now() < deadline) {
            const res = await fetch(`/v1/jobs/${jobId}`);
            if (!res.ok) throw new Error('Job status unavailable');
            const job = await res.json();
            if (job.status === 'ready') return job;
            if (job.status === 'failed') throw new Error(job.error || 'Indexing failed');
            await new Promise(resolve => setTimeout(resolve, 700));
        }
        throw new Error('Indexing timed out');
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
