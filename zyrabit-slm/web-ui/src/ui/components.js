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
/**
 * Safe, regex-based Markdown parser
 * Sanitizes input first to mitigate XSS, then maps constructs.
 */
function parseMarkdown(text) {
    if (!text) return "";
    text = text
        .normalize('NFKC')
        .replace(/[\u200B-\u200D\uFEFF\u00AD]/g, '')
        .replace(/\u00A0/g, ' ')
        .replace(/[ \t]+\n/g, '\n')
        .replace(/\n{3,}/g, '\n\n');
    
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
        codeBlocks.push(`<pre><code class="language-${lang}">${code}</code></pre>`);
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
                :host { display: block; width: 100%; margin-bottom: 1.25rem; animation: slideUp .28s ease-out; }
                @keyframes slideUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
                
                .wrapper { 
                    display: flex; 
                    flex-direction: column;
                    max-width: min(100%, 720px);
                    ${isUser ? 'margin-left: auto; align-items: flex-end;' : 'align-items: flex-start;'} 
                }
                
                .bubble { 
                    padding: 2px 0;
                    border-radius: 0;
                    font-size: 15px;
                    line-height: 1.62;
                    word-break: break-word;
                    position: relative;
                }

                .user { 
                    background: #3f5a6d;
                    color: white; 
                    border-radius: 14px 14px 3px 14px;
                    padding: 11px 15px;
                    line-height: 1.5;
                    max-width: 560px;
                }

                .assistant { 
                    background: transparent;
                    color: #25313a;
                }

                .assistant-label {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    margin-bottom: 8px;
                    color: #607785;
                    font-size: 10px;
                    font-weight: 720;
                    letter-spacing: .06em;
                    text-transform: uppercase;
                }
                .assistant-label::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: #86aebe; }
                .evidence-intro { margin: 0 0 10px; color: #526773; }
                .evidence-excerpt { border: 1px solid #e0e9ea; background: #f7faf9; border-radius: 10px; padding: 0 12px; }
                .evidence-excerpt summary { cursor: pointer; padding: 10px 0; color: #3f5a6d; font-size: 12px; font-weight: 650; }
                .evidence-excerpt .excerpt-body { max-height: 280px; overflow: auto; padding: 0 0 12px; color: #41515a; font-size: 13px; line-height: 1.58; }

                /* Markdown Styling overrides */
                .bubble p {
                    margin: 10px 0;
                }
                .bubble p:first-child { margin-top: 0; }
                .bubble p:last-child { margin-bottom: 0; }
                .bubble ul, .bubble ol {
                    margin: 10px 0;
                    padding-left: 22px;
                }
                .bubble li {
                    margin-bottom: 4px;
                }
                .bubble h1, .bubble h2, .bubble h3 {
                    font-weight: 700;
                    margin-top: 18px;
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
                    background-color: #edf2f3;
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
                    padding: 13px;
                    overflow-x: auto;
                    margin: 10px 0;
                }
                .assistant pre {
                    background: #f5f7f7;
                    border: 1px solid #e3e8e8;
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
                    font-size: 9px;
                    font-weight: bold;
                    text-transform: uppercase;
                    letter-spacing: 0.1em;
                    margin-bottom: 4px;
                    opacity: 0.5;
                    color: ${isUser ? 'white' : '#3f5a6d'};
                }

                .timestamp {
                    font-size: 9px;
                    margin-top: 5px;
                    padding: 0 2px;
                    opacity: .58;
                    font-weight: 600;
                    letter-spacing: .02em;
                    ${isUser ? 'text-align: right; color: rgba(255,255,255,.82);' : 'text-align: left; color: #65737d;'}
                }

                .meta { 
                    font-size: 11px;
                    margin-top: 13px;
                    color: #65737d;
                    font-family: inherit;
                }
                
                .meta summary { cursor: pointer; font-weight: 650; color: #3f5a6d; list-style: none; }
                .meta summary::-webkit-details-marker { display: none; }
                .sources { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }
                .source-pill { background: #f2f5f5; padding: 3px 7px; border-radius: 999px; font-size: 10px; border: 1px solid #e0e7e7; color: #45545e; }
            </style>
            <div class="wrapper">
                ${isTelegram ? `<div class="source-tag">✈️ Telegram</div>` : ''}
                <div class="bubble ${isUser ? 'user' : 'assistant'}">
                    ${!isUser ? `<div class="assistant-label">${this.assistantLabel()}</div>` : ''}
                    <div id="content"></div>
                    ${this.renderMetadata()}
                </div>
                <div class="timestamp">${this._timestamp}</div>
            </div>
        `;
        const content = this.shadowRoot.getElementById('content');
        const cleanText = (this._text || '')
            .replace(/\n?\[EVIDENCE:[0-9a-fA-F-]{36}\]/g, '')
            .replace(/\n{0,2}(?:evidencia|evidence|fuente|source):\s*$/i, '')
            .trim();
        if (this._metadata?.decision === 'evidence-extractive-fallback') {
            content.innerHTML = `<p class="evidence-intro">No pude validar una redacción del modelo. Te dejo el pasaje recuperado para que lo revises directamente.</p><details class="evidence-excerpt"><summary>Ver pasaje verificable</summary><div class="excerpt-body">${parseMarkdown(cleanText.replace(/^No puedo verificar[\s\S]*?documento seleccionado:\s*/i, ''))}</div></details>`;
        } else {
            content.innerHTML = parseMarkdown(cleanText);
        }
    }


    assistantLabel() {
        const decision = this._metadata?.decision;
        if (decision === 'conversation-greeting' || decision === 'conversation-acknowledgement' || decision === 'conversation-clarification' || decision === 'profile-welcome') return 'Zyra · contigo';
        if (this._metadata?.sources?.length) return 'Zyra · evidencia local';
        return 'Zyra';
    }



    renderMetadata() {
        if (!this._metadata) return '';
        const m = this._metadata;
        const escapeHtml = (value) => String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\"/g, '&quot;').replace(/'/g, '&#039;');
        const sources = m.sources ? m.sources.map(source => {
            if (typeof source === 'string') return `<span class="source-pill">${escapeHtml(source)}</span>`;
            const location = source.locator?.page ? `p. ${source.locator.page}` : source.locator?.sheet ? `${source.locator.sheet} ${source.locator.range || ''}` : source.locator?.slide ? `slide ${source.locator.slide}` : 'evidence';
            return `<span class="source-pill" title="${escapeHtml(source.excerpt || '')}">${escapeHtml(source.filename || 'document')} · ${escapeHtml(location)}</span>`;
        }).join('') : '';
        const latency = m.latency_seconds != null ? ` · ${(Number(m.latency_seconds) * 1000).toFixed(0)} ms` : '';
        const decisionLabels = {
            'library-empty-greeting': 'Biblioteca vacía · bienvenida',
            'library-empty-guidance': 'Biblioteca vacía · siguiente paso',
            'library-indexing-guidance': 'Documento en preparación',
            'profile-welcome': 'Espacio configurado',
            'session-restored': 'Conversación restaurada',
            'conversation-greeting': 'Conversación local',
            'conversation-acknowledgement': 'Conversación local',
            'conversation-clarification': 'Conversación local',
            'model-knowledge': 'Consultado con el modelo local',
            'model-with-evidence': 'Modelo local + documentos consultados',
            'evidence-not-found': 'Sin evidencia para esta pregunta',
            'selected-document-unavailable': 'Documento no disponible',
            'evidence-query': 'Respuesta basada en evidencia',
            'evidence-query-lexical': 'Respuesta basada en evidencia léxica',
            'evidence-extractive-fallback': 'Fragmento verificable',
            'inference-unavailable': 'Motor local no disponible',
        };
        const decision = escapeHtml(decisionLabels[m.decision] || 'Estado de consulta no especificado');

        return `
            <div class="meta">${decision}${latency}</div>
            ${sources ? `<details class="meta"><summary>Sources · ${m.rag_hits || 0} passages</summary><div class="sources">${sources}</div></details>` : ''}
        `;
    }
}

customElements.define('zyra-status-dot', ZyraStatusDot);
customElements.define('zyra-chat-message', ZyraChatMessage);
