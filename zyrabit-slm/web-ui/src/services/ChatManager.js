import { bus } from "../core/EventBus";
import { Storage } from "../adapters/Storage";
import { EVENTS } from "../core/Constants";

/**
 * ChatManager (Domain Service)
 * Manages message lifecycle, queue, and idempotency.
 */
export class ChatManager {
    constructor() {
        this.queue = Storage.load('pending_messages') || [];
        this.sessionId = Storage.load('session_id');
        if (!this.sessionId) {
            this.sessionId = this.generateSessionId();
            Storage.save('session_id', this.sessionId);
        }
        this.isProcessing = false;
        this.pendingTimeout = null;
        this.setupListeners();
    }

    setupListeners() {
        bus.on(EVENTS.CHAT.SEND, (data) => this.enqueue(data));
        bus.on(EVENTS.CHAT.RESPONSE_RECEIVED, (data) => this.onResponse(data));
        bus.on(EVENTS.SYSTEM.GATEWAY_CONNECTED, () => this.onGatewayConnected());
        bus.on(EVENTS.SYSTEM.GATEWAY_DISCONNECTED, () => this.onGatewayDisconnected());
    }


    enqueue(data) {
        const message = {
            id: crypto.randomUUID(),
            text: data.text,
            history: data.history || [],
            timestamp: Date.now()
        };
        this.queue.push(message);
        this.persist();

        bus.emit(EVENTS.UI.MSG_ADDED, { role: 'user', text: data.text });


        if (!this.isProcessing) {
            this.processNext();
        }
    }

    clearPendingTimeout() {
        if (this.pendingTimeout) {
            clearTimeout(this.pendingTimeout);
            this.pendingTimeout = null;
        }
    }

    async processNext() {
        if (this.queue.length === 0) {
            this.isProcessing = false;
            this.clearPendingTimeout();
            bus.emit(EVENTS.UI.THINKING, false);
            return;
        }

        this.isProcessing = true;
        bus.emit(EVENTS.UI.THINKING, true);

        const message = this.queue[0];
        const chip = document.getElementById('active-context-chip');
        const documentId = chip?.dataset?.documentId || null;
        try {
            const response = await fetch('/v1/query', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: message.text, session_id: this.sessionId, document_id: documentId })
            });
            if (!response.ok) throw new Error(`HTTP_${response.status}`);
            this.onResponse(await response.json());
        } catch (error) {
            this.onResponse({ response: 'No pude completar la consulta local. Revisa que el nodo y el motor de inferencia estén listos.', metadata: { decision: 'request-failed', sources: [] } });
        }
    }

    handleRequestTimeout() {
        this.isProcessing = false;
        this.clearPendingTimeout();
        bus.emit(EVENTS.UI.THINKING, false);

        bus.emit(EVENTS.SYSTEM.LOG, {
            type: 'WARNING',
            event: 'REQUEST_TIMEOUT',
            message: "La conexión está inestable o lenta. Reintentando..."
        });
    }

    onGatewayConnected() {
        console.log("🔌 Gateway reconnected. Checking pending queue...");
        if (this.queue.length > 0) {
            this.processNext();
        }
    }

    onGatewayDisconnected() {
        console.warn("🔌 Gateway disconnected. Suspending chat processing...");
        this.clearPendingTimeout();
        this.isProcessing = false;
        bus.emit(EVENTS.UI.THINKING, false);
    }

    onResponse(data) {
        this.clearPendingTimeout();
        const isNotification = data.metadata?.source === 'TELEGRAM';

        // Only shift if we were expecting a response from the web UI
        if (!isNotification && this.queue.length > 0) {
            this.queue.shift();
            this.persist();
        }

        bus.emit(EVENTS.UI.MSG_ADDED, {
            role: 'assistant',
            text: data.response,
            metadata: data.metadata
        });

        if (data.metadata?.command === '/clear') {
            this.sessionId = this.generateSessionId();
            Storage.save('session_id', this.sessionId);
            bus.emit('UI:CLEAR_CHAT');
        }

        // If there's more in the queue, keep going
        if (this.queue.length > 0) {
            this.processNext();
        } else if (!isNotification) {
            // Only stop thinking if this wasn't just a notification bridge message
            this.isProcessing = false;
            bus.emit(EVENTS.UI.THINKING, false);
        }
    }

    generateSessionId() {
        if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
            return crypto.randomUUID();
        }
        if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
            const bytes = new Uint8Array(16);
            crypto.getRandomValues(bytes);
            return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
        }
        throw new Error('Secure random number generator is unavailable for session ID generation.');
    }

    async resetSession() {
        try { await fetch(`/v1/sessions/${this.sessionId}`, { method: 'DELETE' }); } catch (_) { /* local reset still works */ }
        this.sessionId = this.generateSessionId();
        Storage.save('session_id', this.sessionId);
    }

    persist() {
        Storage.save('pending_messages', this.queue);
    }

    recover() {
        if (this.queue.length > 0) {
            console.log("Recovering shadow state:", this.queue.length, "messages");
            this.processNext();
        }
    }
}
