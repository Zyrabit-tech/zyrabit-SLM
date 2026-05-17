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

    set data({ role, text, metadata, timestamp }) {
        this._role = role;
        this._text = text;
        this._metadata = metadata;
        this._timestamp = timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        this.render();
    }

    render() {
        const isUser = this._role === 'user';
        const source = this._metadata?.source;
        const isTelegram = source === 'TELEGRAM' || source === 'TELEGRAM_INCOMING';

        this.shadowRoot.innerHTML = `
            <style>
                :host { display: block; width: 100%; margin-bottom: 0.75rem; animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
                @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
                
                .wrapper { 
                    display: flex; 
                    flex-direction: column;
                    max-width: 80%; 
                    ${isUser ? 'margin-left: auto; align-items: flex-end;' : 'align-items: flex-start;'} 
                }
                
                .bubble { 
                    padding: 12px 16px; 
                    border-radius: 1.25rem; 
                    font-size: 14.5px; 
                    line-height: 1.45; 
                    word-break: break-word;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
                    position: relative;
                }

                .user { 
                    background: #3f5a6d; 
                    color: white; 
                    border-top-right-radius: 4px;
                    box-shadow: 0 4px 15px rgba(63, 90, 109, 0.15);
                }

                .assistant { 
                    background: white; 
                    color: #323439; 
                    border: 1px solid rgba(0,0,0,0.03);
                    border-top-left-radius: 4px;
                }

                .source-tag {
                    font-size: 8px;
                    font-bold;
                    text-transform: uppercase;
                    letter-spacing: 0.1em;
                    margin-bottom: 4px;
                    opacity: 0.5;
                    color: ${isUser ? 'white' : '#3f5a6d'};
                }

                .timestamp {
                    font-size: 9px;
                    margin-top: 4px;
                    opacity: 0.5;
                    font-weight: 700;
                    letter-spacing: 0.02em;
                    ${isUser ? 'text-align: right; color: rgba(255,255,255,0.8);' : 'text-align: left; color: #3f5a6d;'}
                }

                .meta { 
                    font-size: 9px; 
                    margin-top: 8px; 
                    padding-top: 8px;
                    border-top: 1px solid rgba(0,0,0,0.05);
                    opacity: 0.6; 
                    font-family: monospace; 
                    display: flex; 
                    flex-direction: column; 
                    gap: 4px; 
                }
                
                .sources { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
                .source-pill { background: rgba(63, 90, 109, 0.05); padding: 2px 4px; border-radius: 4px; font-size: 8px; border: 1px solid rgba(63, 90, 109, 0.1); }
            </style>
            <div class="wrapper">
                ${isTelegram ? `<div class="source-tag">✈️ Telegram</div>` : ''}
                <div class="bubble ${isUser ? 'user' : 'assistant'}">
                    <div id="content"></div>
                    ${this.renderMetadata()}
                    <div class="timestamp">${this._timestamp}</div>
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
