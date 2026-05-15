import { bus } from "../core/EventBus";
import { Storage } from "../adapters/Storage";

/**
 * ChatManager (Domain Service)
 * Manages message lifecycle, queue, and idempotency.
 */
export class ChatManager {
    constructor() {
        this.queue = Storage.load('pending_messages') || [];
        this.isProcessing = false;
        this.setupListeners();
    }

    setupListeners() {
        bus.on('CHAT:SEND', (text) => this.enqueue(text));
        bus.on('CHAT:RESPONSE_RECEIVED', (data) => this.onResponse(data));
    }

    enqueue(text) {
        const message = {
            id: crypto.randomUUID(),
            text,
            timestamp: Date.now()
        };
        this.queue.push(message);
        this.persist();
        
        bus.emit('UI:MSG_ADDED', { role: 'user', text });
        
        if (!this.isProcessing) {
            this.processNext();
        }
    }

    processNext() {
        if (this.queue.length === 0) {
            this.isProcessing = false;
            bus.emit('UI:THINKING', false);
            return;
        }

        this.isProcessing = true;
        bus.emit('UI:THINKING', true);
        
        const message = this.queue[0];
        bus.emit('SOCKET:EMIT', { 
            text: message.text, 
            client_msg_id: message.id 
        });
    }

    onResponse(data) {
        // Only shift if we were expecting a response
        if (this.queue.length > 0) {
            this.queue.shift();
            this.persist();
        }
        
        bus.emit('UI:MSG_ADDED', { 
            role: 'assistant', 
            text: data.response, 
            metadata: data.metadata 
        });
        
        // If there's more in the queue, keep going
        if (this.queue.length > 0) {
            this.processNext();
        } else {
            this.isProcessing = false;
            bus.emit('UI:THINKING', false);
        }
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
