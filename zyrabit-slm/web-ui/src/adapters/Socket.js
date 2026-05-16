import { io } from "socket.io-client";
import { bus } from "../core/EventBus";
import { EVENTS } from "../core/Constants";

/**
 * Socket Adapter V5.2
 * Implements Zero-Trust connectivity with pre-flight checks and retry limits.
 */
export class SocketAdapter {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxAttempts = 5;
        this.timeoutMs = 60000;
        this.isConnecting = false;
        this.setupBusListeners();
    }


    async connect() {
        if (this.isConnecting || (this.socket && this.socket.connected)) return;
        
        this.isConnecting = true;
        const socketUrl = window.location.origin;

        // 1. Pre-flight Connectivity Test
        try {
            const healthCheck = await fetch(`${socketUrl}/v1/health`, { signal: AbortSignal.timeout(3000) });
            if (!healthCheck.ok) throw new Error("Backend not ready");
        } catch (e) {
            console.warn("⚠️ Gateway Pre-flight failed. Retrying in background...");
            this.handleConnectionFailure();
            return;
        }

        // 2. Initialize Socket with strict limits
        this.socket = io(socketUrl, { 
            path: "/socket.io",
            reconnectionAttempts: this.maxAttempts,
            timeout: 5000,
            autoConnect: true
        });

        this.setupSocketEvents();
    }

    setupSocketEvents() {
        this.socket.on("connect", () => {
            this.reconnectAttempts = 0;
            this.isConnecting = false;
            console.log("🚀 Secure Gateway Established");
            bus.emit(EVENTS.SYSTEM.LOG, { type: 'SYSTEM', event: 'SECURE_GATEWAY_ESTABLISHED' });
        });

        this.socket.on("chat_response", (data) => {
            bus.emit(EVENTS.CHAT.RESPONSE_RECEIVED, data);
        });


        this.socket.on("connect_error", (err) => {
            this.reconnectAttempts++;
            if (this.reconnectAttempts >= this.maxAttempts) {
                this.handleConnectionFailure(true);
            }
        });

        this.socket.on("disconnect", (reason) => {
            console.warn(`⚠️ Gateway Disconnected: ${reason}`);
            bus.emit(EVENTS.SYSTEM.LOG, { type: 'WARNING', event: 'GATEWAY_DISCONNECTED' });
            if (reason === "io server disconnect") {

                // Server-side disconnect, don't auto-reconnect
                this.socket.close();
            }
        });
    }

    handleConnectionFailure(permanent = false) {
        this.isConnecting = false;
        if (permanent) {
            console.error("❌ Gateway Connection Timeout. Switching to Offline Mode.");
            if (this.socket) this.socket.close();
            bus.emit(EVENTS.SYSTEM.LOG, { type: 'ERROR', event: 'GATEWAY_TIMEOUT_OFFLINE' });
        } else {

            // Soft retry after 10s if not permanent
            setTimeout(() => this.connect(), 10000);
        }
    }

    setupBusListeners() {
        bus.on(EVENTS.SOCKET.EMIT, (data) => {
            if (this.socket && this.socket.connected) {
                this.socket.emit("chat_message", data);
            } else {
                bus.emit(EVENTS.SYSTEM.LOG, { type: 'ERROR', event: 'SOCKET_NOT_CONNECTED' });
            }
        });
    }

}
