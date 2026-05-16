/**
 * Zyrabit Sovereign Web Components
 * Pure Custom Elements without dependencies.
 */

/**
 * <zyra-status-dot>
 * Managed status indicator for infrastructure services.
 */
class ZyraStatusDot extends HTMLElement {
    static get observedAttributes() { return ['status', 'label']; }

    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.render();
    }

    attributeChangedCallback() {
        this.render();
    }

    render() {
        const status = (this.getAttribute('status') || 'offline').toUpperCase();
        const label = this.getAttribute('label') || '';
        const isOnline = status === 'ONLINE' || status === 'CONNECTED';

        this.shadowRoot.innerHTML = `
            <style>
                :host { display: inline-flex; align-items: center; gap: 8px; font-family: inherit; }
                .dot { width: 8px; height: 8px; border-radius: 50%; transition: all 0.3s ease; }
                .online { background-color: #10b981; box-shadow: 0 0 8px rgba(16, 185, 129, 0.4); }
                .offline { background-color: #ef4444; box-shadow: 0 0 8px rgba(239, 68, 68, 0.4); }
                .text { font-size: 10px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.05em; }
                .text-online { color: #059669; }
                .text-offline { color: #dc2626; }
            </style>
            <div class="dot ${isOnline ? 'online' : 'offline'}"></div>
            <div class="text ${isOnline ? 'text-online' : 'text-offline'}">${label || status}</div>
        `;
    }
}

/**
 * <zyra-chat-message>
 * Encapsulated chat bubble with metadata support.
 */
class ZyraChatMessage extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    set data({ role, text, metadata }) {
        this._role = role;
        this._text = text;
        this._metadata = metadata;
        this.render();
    }

    render() {
        const isUser = this._role === 'user';
        
        this.shadowRoot.innerHTML = `
            <style>
                :host { display: block; width: 100%; margin-bottom: 1rem; animation: slideIn 0.3s ease-out; }
                @keyframes slideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
                .wrapper { display: flex; gap: 12px; max-width: 85%; align-items: flex-start; ${isUser ? 'flex-direction: row-reverse; margin-left: auto;' : ''} }
                .avatar { width: 32px; height: 32px; border-radius: 50%; background: #e2ecf4; border: 1px solid #a9c4d9; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
                .avatar img { width: 20px; height: 20px; object-fit: contain; }
                .bubble { padding: 16px; border-radius: 20px; font-size: 14px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
                .user { background: #3f5a6d; color: white; border-top-right-radius: 0; }
                .assistant { background: #e2ecf4; color: #323439; border: 1px solid rgba(169, 196, 217, 0.5); border-top-left-radius: 0; }
                .meta { font-size: 9px; margin-top: 8px; opacity: 0.6; font-family: monospace; display: flex; flex-direction: column; gap: 4px; }
                .sources { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
                .source-pill { background: rgba(63, 90, 109, 0.1); padding: 2px 4px; border-radius: 4px; font-size: 8px; border: 1px solid rgba(63, 90, 109, 0.2); }
            </style>
            <div class="wrapper">
                ${!isUser ? `<div class="avatar"><img src="/img/logo.png"></div>` : ''}
                <div class="bubble ${isUser ? 'user' : 'assistant'}">
                    <div id="content"></div>
                    ${this.renderMetadata()}
                </div>
            </div>
        `;
        this.shadowRoot.getElementById('content').textContent = this._text;
    }

    renderMetadata() {
        if (!this._metadata) return '';
        const m = this._metadata;
        const sources = m.sources ? [...new Set(m.sources)].map(s => `<span class="source-pill">${s}</span>`).join('') : '';
        
        return `
            <div class="meta">
                <span>${(m.decision || 'direct').toUpperCase()} | ${m.latency_ms || 0}ms | HITS: ${m.rag_hits || 0}</span>
                ${sources ? `<div class="sources"><strong>SOURCES:</strong> ${sources}</div>` : ''}
            </div>
        `;
    }
}

customElements.define('zyra-status-dot', ZyraStatusDot);
customElements.define('zyra-chat-message', ZyraChatMessage);
