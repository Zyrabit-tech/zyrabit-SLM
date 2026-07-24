/**
 * Zyrabit Sovereign Web Components
 * Pure Custom Elements without dependencies.
 */

/**
 * Minimal HTML escaper — prevents XSS when interpolating
 * server-controlled or user-controlled values into innerHTML.
 * @param {unknown} value
 * @returns {string}
 */
function escapeHtml(value) {
    const str = String(value ?? '');
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

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
/**
 * Safe, regex-based Markdown parser
 * Sanitizes input first to mitigate XSS, then maps constructs.
 */
function parseMarkdown(text) {
    if (!text) return "";
    
    // 1. Escape HTML special characters for XSS prevention
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Temp array to protect code blocks from subsequent markdown regexes
    const codeBlocks = [];
    
    // 2. Multiline code blocks: ```lang\ncode\n```
    html = html.replace(/```([\s\S]*?)```/g, (match, codeContent) => {
        let lang = "";
        let code = codeContent;
        const firstNewLine = codeContent.indexOf("\n");
        if (firstNewLine !== -1) {
            const potentialLang = codeContent.substring(0, firstNewLine).trim();
            if (potentialLang && potentialLang.length < 15 && !potentialLang.includes(" ")) {
                lang = potentialLang;
                code = codeContent.substring(firstNewLine + 1);
            }
        }
        code = code.trim();
        const placeholder = `__CODE_BLOCK_PLACEHOLDER_${codeBlocks.length}__`;
        // Escape lang attribute to prevent attribute injection (e.g. lang="" onload=...)
        const safeLang = lang.replace(/[^a-zA-Z0-9-]/g, '');
        codeBlocks.push(`<pre><code class="language-${safeLang}">${code}</code></pre>`);
        return placeholder;
    });

    // 3. Inline code: `code`
    const inlineCodes = [];
    html = html.replace(/`([^`\n]+)`/g, (match, code) => {
        const placeholder = `__INLINE_CODE_PLACEHOLDER_${inlineCodes.length}__`;
        inlineCodes.push(`<code>${code}</code>`);
        return placeholder;
    });

    // 4. Headers: ### , ## , # (supports inline bold/etc. too)
    html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');

    // 5. Bold: **text**
    html = html.replace(/\*\*([\s\S]*?)\*\*/g, '<strong>$1</strong>');

    // 6. Italic: *text* or _text_
    html = html.replace(/\*([\s\S]*?)\*/g, '<em>$1</em>');
    html = html.replace(/_([\s\S]*?)_/g, '<em>$1</em>');

    // 7. Lists
    // Bullet lists: - item or * item
    html = html.replace(/^\s*[-*]\s+(.*?)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*?<\/li>\s*)+/gs, (match) => {
        return `<ul>${match.trim()}</ul>`;
    });

    // Numbered lists: 1. item
    html = html.replace(/^\s*(\d+)\.\s+(.*?)$/gm, '<li class="numbered">$2</li>');
    html = html.replace(/(<li class="numbered">.*?<\/li>\s*)+/gs, (match) => {
        const cleaned = match.replace(/class="numbered"/g, '');
        return `<ol>${cleaned.trim()}</ol>`;
    });

    // 8. Paragraphs: split by double newlines, wrap in <p>, unless they start with block tags or placeholders
    const paragraphs = html.split(/\n\n+/);
    html = paragraphs.map(p => {
        p = p.trim();
        if (!p) return "";
        if (p.startsWith('<h') || p.startsWith('<ul') || p.startsWith('<ol') || p.startsWith('<pre') || p.startsWith('__CODE_BLOCK_PLACEHOLDER_')) {
            return p;
        }
        // Convert single newlines to <br> for readability inside paragraph blocks
        p = p.replace(/\n/g, '<br>');
        return `<p>${p}</p>`;
    }).join('');

    // Restore inline code tags
    inlineCodes.forEach((val, i) => {
        html = html.split(`__INLINE_CODE_PLACEHOLDER_${i}__`).join(val);
    });

    // Restore code block tags
    codeBlocks.forEach((val, i) => {
        html = html.split(`__CODE_BLOCK_PLACEHOLDER_${i}__`).join(val);
    });

    return html;
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

                /* Markdown Styling overrides */
                .bubble p {
                    margin: 8px 0;
                }
                .bubble p:first-child { margin-top: 0; }
                .bubble p:last-child { margin-bottom: 0; }
                .bubble ul, .bubble ol {
                    margin: 8px 0;
                    padding-left: 20px;
                }
                .bubble li {
                    margin-bottom: 4px;
                }
                .bubble h1, .bubble h2, .bubble h3 {
                    font-weight: 700;
                    margin-top: 14px;
                    margin-bottom: 6px;
                }
                .assistant h1, .assistant h2, .assistant h3 { color: #1e293b; }
                .user h1, .user h2, .user h3 { color: white; }
                
                .bubble h1 { font-size: 1.15rem; }
                .bubble h2 { font-size: 1.1rem; }
                .bubble h3 { font-size: 1.05rem; }
                
                .assistant strong { color: #0f172a; font-weight: 700; }
                .user strong { color: white; font-weight: 700; }
                
                .bubble code {
                    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
                    font-size: 12.5px;
                    padding: 2px 5px;
                    border-radius: 4px;
                    font-weight: 500;
                }
                .assistant code {
                    background-color: rgba(63, 90, 109, 0.08);
                    color: #3f5a6d;
                }
                .user code {
                    background-color: rgba(255, 255, 255, 0.15);
                    color: white;
                }

                .bubble pre {
                    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
                    font-size: 12.5px;
                    border-radius: 8px;
                    padding: 12px;
                    overflow-x: auto;
                    margin: 10px 0;
                }
                .assistant pre {
                    background: #f8fafc;
                    border: 1px solid rgba(0, 0, 0, 0.05);
                }
                .user pre {
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                }

                .bubble pre code {
                    background: none;
                    padding: 0;
                    border-radius: 0;
                }
                .assistant pre code { color: #334155; }
                .user pre code { color: white; }

                .source-tag {
                    font-size: 8px;
                    font-weight: bold;
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
        this.shadowRoot.getElementById('content').innerHTML = parseMarkdown(this._text);
    }



    renderMetadata() {
        if (!this._metadata) return '';
        const m = this._metadata;
        // SECURITY: Escape all server-controlled values before HTML interpolation
        // Source filenames, decision strings, and numeric metadata come from the API
        // and could contain HTML/JS if the model output is manipulated.
        const sources = m.sources
            ? [...new Set(m.sources)].map(s => `<span class="source-pill">${escapeHtml(s)}</span>`).join('')
            : '';
        const decision = escapeHtml((m.decision || 'direct').toUpperCase());
        const latency  = escapeHtml(m.latency_ms  ?? 0);
        const hits     = escapeHtml(m.rag_hits     ?? 0);

        return `
            <div class="meta">
                <span>${decision} | ${latency}ms | HITS: ${hits}</span>
                ${sources ? `<div class="sources"><strong>SOURCES:</strong> ${sources}</div>` : ''}
            </div>
        `;
    }
}

customElements.define('zyra-status-dot', ZyraStatusDot);
customElements.define('zyra-chat-message', ZyraChatMessage);
