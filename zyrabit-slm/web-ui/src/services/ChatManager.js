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
        this.isProcessing = false;
        this.setupListeners();
    }

    setupListeners() {
        bus.on(EVENTS.CHAT.SEND, (data) => this.enqueue(data));
        bus.on(EVENTS.CHAT.RESPONSE_RECEIVED, (data) => this.onResponse(data));
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

    processNext() {
        if (this.queue.length === 0) {
            this.isProcessing = false;
            bus.emit(EVENTS.UI.THINKING, false);
            return;
        }

        this.isProcessing = true;
        bus.emit(EVENTS.UI.THINKING, true);
        
        const message = this.queue[0];
        bus.emit(EVENTS.SOCKET.EMIT, { 
            text: message.text, 
            history: message.history,
            client_msg_id: message.id 
        });
    }

    onResponse(data) {
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
        
        // If there's more in the queue, keep going
        if (this.queue.length > 0) {
            this.processNext();
        } else if (!isNotification) {
            // Only stop thinking if this wasn't just a notification bridge message
            this.isProcessing = false;
            bus.emit(EVENTS.UI.THINKING, false);
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
