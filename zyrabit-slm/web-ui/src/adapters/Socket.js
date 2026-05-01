import { io } from "socket.io-client";
import { bus } from "../core/EventBus";

/**
 * Socket Adapter
 * Connects the EventBus to the real-time server.
 */
export class SocketAdapter {
    constructor() {
        this.socket = null;
        this.setupBusListeners();
    }

    connect() {
        const socketUrl = window.location.origin;
        this.socket = io(socketUrl, { path: "/socket.io" });

        this.socket.on("connect", () => {
            console.log("Secure Gateway Connected");
            bus.emit('SYSTEM:LOG', { type: 'SYSTEM', event: 'SECURE_GATEWAY_ESTABLISHED' });
        });

        this.socket.on("chat_response", (data) => {
            bus.emit('CHAT:RESPONSE_RECEIVED', data);
        });

        this.socket.on("disconnect", () => {
            bus.emit('SYSTEM:LOG', { type: 'WARNING', event: 'GATEWAY_DISCONNECTED' });
        });
    }

    setupBusListeners() {
        bus.on('SOCKET:EMIT', (data) => {
            if (this.socket) {
                this.socket.emit("chat_message", data);
            }
        });
    }
}
