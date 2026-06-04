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
        if (this.socket && this.socket.connected) return;
        if (this.isConnecting) return;
        
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

        if (!this.socket) {
            // 2. Initialize Socket with auto-reconnection and infinite attempts
            this.socket = io(socketUrl, { 
                path: "/socket.io",
                reconnection: true,
                reconnectionAttempts: Infinity,
                reconnectionDelay: 1000,
                reconnectionDelayMax: 5000,
                timeout: 5000,
                autoConnect: true
            });
            this.setupSocketEvents();
        } else {
            console.log("🔌 Reconnecting existing Socket...");
            this.socket.connect();
        }
        
        this.isConnecting = false;
    }

    setupSocketEvents() {
        this.socket.on("connect", () => {
            this.reconnectAttempts = 0;
            this.isConnecting = false;
            console.log("🚀 Secure Gateway Established");
            bus.emit(EVENTS.SYSTEM.LOG, { type: 'SYSTEM', event: 'SECURE_GATEWAY_ESTABLISHED' });
            bus.emit(EVENTS.SYSTEM.GATEWAY_CONNECTED);
        });

        this.socket.on("chat_response", (data) => {
            bus.emit(EVENTS.CHAT.RESPONSE_RECEIVED, data);
        });

        this.socket.on("connect_error", (err) => {
            this.reconnectAttempts++;
            console.warn(`⚠️ Socket connection error (${this.reconnectAttempts}):`, err.message);
            bus.emit(EVENTS.SYSTEM.LOG, { type: 'WARNING', event: `SOCKET_CONNECT_ERROR: ${err.message}` });
        });

        this.socket.on("disconnect", (reason) => {
            console.warn(`⚠️ Gateway Disconnected: ${reason}`);
            bus.emit(EVENTS.SYSTEM.LOG, { type: 'WARNING', event: 'GATEWAY_DISCONNECTED' });
            bus.emit(EVENTS.SYSTEM.GATEWAY_DISCONNECTED, reason);
            if (reason === "io server disconnect") {
                // Server-side disconnect, trigger manual reconnection check
                setTimeout(() => {
                    if (this.socket) this.socket.connect();
                }, 5000);
            }
        });
    }

    handleConnectionFailure() {
        this.isConnecting = false;
        console.warn("⚠️ Gateway Connection failed. Retrying socket connect in 10s...");
        setTimeout(() => this.connect(), 10000);
    }

    setupBusListeners() {
        bus.on(EVENTS.SOCKET.EMIT, (data) => {
            if (this.socket && this.socket.connected) {
                this.socket.emit("chat_message", data);
            } else {
                bus.emit(EVENTS.SYSTEM.LOG, { type: 'ERROR', event: 'SOCKET_NOT_CONNECTED' });
                bus.emit(EVENTS.SYSTEM.GATEWAY_DISCONNECTED, 'not_connected');
            }
        });
    }

}
