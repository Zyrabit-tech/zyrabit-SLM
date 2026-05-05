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
        
        this.init();
    }

    init() {
        this.setupUIListeners();
        this.socket.connect();
        this.startHealthChecks();
        this.chat.recover(); // Recover Shadow State
        this.loadVault();
    }

    setupUIListeners() {
        // Chat Form
        const form = document.getElementById('chat-form');
        const input = document.getElementById('chat-input');
        form.onsubmit = (e) => {
            e.preventDefault();
            if (!input.value.trim()) return;
            bus.emit('CHAT:SEND', input.value);
            input.value = '';
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
        const updateHealth = async () => {
            try {
                const res = await fetch('/v1/health');
                if (!res.ok) throw new Error(`HTTP_${res.status}`);
                const data = await res.json();
                this.updateUIStatus(data);
            } catch (e) {
                this.addGdprLog("SYSTEM", `HEALTH_CHECK_FAILED`);
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

        setStatus('health-api', 'online');
        setStatus('health-slm', data.slm);
        setStatus('health-db', data.db);

        const modelBadge = document.getElementById('model-badge');
        modelBadge.innerText = `MODEL: ${data.model || '...'}`;
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

    async handleFileUpload(files) {
        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);
            this.addGdprLog("INGEST", `PROCESSING_${file.name.toUpperCase()}`);
            try {
                const res = await fetch('/v1/ingest', { method: 'POST', body: formData });
                if (!res.ok) throw new Error(`HTTP_${res.status}`);
                await this.loadVault();
                this.addGdprLog("INGEST", `SUCCESS_${file.name.toUpperCase()}`);
            } catch (e) {
                this.addGdprLog("INGEST", `FAILED_${file.name.toUpperCase()}`);
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ZyrabitApp();
});
