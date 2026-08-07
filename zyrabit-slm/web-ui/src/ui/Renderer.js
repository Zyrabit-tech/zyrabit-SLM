import { bus } from "../core/EventBus";
import { EVENTS, IDS } from "../core/Constants";
import { getSafeElement } from "../utils/DOM";

/**
 * Renderer (UI Component)
 * Pure DOM manipulation with XSS protection.
 */
export class Renderer {
    constructor() {
        this.container = getSafeElement(IDS.CHAT_CONTAINER);
        this.lastDate = null;
        this.setupListeners();
    }


    setupListeners() {
        bus.on(EVENTS.UI.MSG_ADDED, (data) => this.renderMessage(data.role, data.text, data.metadata, data.timestamp));
        bus.on(EVENTS.UI.THINKING, (state) => this.toggleThinking(state));
        bus.on('UI:CLEAR_CHAT', () => {
            this.container.innerHTML = '';
            this.lastDate = null;
            const suggestions = document.getElementById('floating-suggestions');
            if (suggestions) {
                suggestions.style.display = 'flex';
                suggestions.style.opacity = '1';
            }
        });
    }


    renderMessage(role, text, metadata = null, timestamp = null) {
        const now = new Date();
        const timeStr = timestamp || now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // User requested Telegram incoming messages to look like user messages
        let effectiveRole = role;
        if (metadata && (metadata.source === 'TELEGRAM' || metadata.source === 'TELEGRAM_INCOMING')) {
            effectiveRole = 'user';
        }

        const msg = document.createElement('zyra-chat-message');
        msg.data = { role: effectiveRole, text, metadata, timestamp: timeStr };
        
        this.container.appendChild(msg);

        if (metadata?.sources) {
            window.dispatchEvent(new CustomEvent('zyra:sources', { detail: metadata.sources }));
        }
        
        // Auto-scroll to bottom
        requestAnimationFrame(() => {
            this.container.scrollTo({
                top: this.container.scrollHeight,
                behavior: 'smooth'
            });
        });
    }




    createMessageWrapper(role) {
        const wrapper = document.createElement('div');
        wrapper.className = `flex items-start gap-3 max-w-[85%] ${role === 'user' ? 'flex-row-reverse' : ''}`;

        if (role === 'assistant') {
            const avatar = document.createElement('div');
            avatar.className = 'w-8 h-8 rounded-full bg-zyrabit-surface border border-zyrabit-border flex items-center justify-center flex-shrink-0 mt-1 shadow-sm';
            avatar.innerHTML = `<img src="/img/logo.png" class="w-5 h-5 object-contain">`;
            wrapper.appendChild(avatar);
        }
        return wrapper;
    }

    createMessageBubble(role, text) {
        const bubble = document.createElement('div');
        bubble.className = `p-4 rounded-2xl text-sm ${role === 'user' ? 'bg-zyrabit-primary text-white rounded-tr-none' : 'bg-zyrabit-surface text-zyrabit-text border border-zyrabit-border/50 rounded-tl-none'}`;
        bubble.textContent = text; // XSS SAFE!
        return bubble;
    }


    renderMetadata(parent, metadata) {
        const meta = document.createElement('div');
        meta.className = 'text-[9px] mt-2 opacity-50 font-mono flex flex-col gap-1';
        
        const stats = document.createElement('span');
        stats.textContent = `${metadata.decision.toUpperCase()} | ${metadata.latency_ms}ms | HITS: ${metadata.rag_hits}`;
        meta.appendChild(stats);
        
        if (metadata.sources && metadata.sources.length > 0) {
            const sourceContainer = document.createElement('div');
            sourceContainer.className = 'flex flex-wrap gap-1 mt-1';
            
            const sourceLabel = document.createElement('span');
            sourceLabel.className = 'opacity-70 font-bold';
            sourceLabel.textContent = 'SOURCES:';
            sourceContainer.appendChild(sourceLabel);
            
            [...new Set(metadata.sources)].forEach(s => {
                const sPill = document.createElement('span');
                sPill.className = 'bg-zyrabit-primary/10 px-1 rounded text-[8px] border border-zyrabit-primary/20';
                sPill.textContent = s; // XSS SAFE!
                sourceContainer.appendChild(sPill);
            });
            meta.appendChild(sourceContainer);
        }
        parent.appendChild(meta);
    }

    toggleThinking(state) {
        const button = document.getElementById('chat-submit');
        const loader = document.getElementById('thinking-bubble');
        const input = document.getElementById(IDS.CHAT_INPUT);
        if (!button) return;

        const btnText = button.querySelector('.button-text');
        const btnSpinner = button.querySelector('.loader-ios');

        if (state) {
            button.disabled = true;
            button.classList.add('opacity-80', 'cursor-not-allowed');
            if (input) {
                input.disabled = true;
                input.classList.add('opacity-80', 'cursor-not-allowed');
            }
            if (btnText) btnText.classList.add('hidden');
            if (btnSpinner) btnSpinner.classList.remove('hidden');
            
            if (loader) return;

            const newLoader = document.createElement('div');
            newLoader.id = 'thinking-bubble';
            newLoader.className = 'thinking-bubble';
            newLoader.innerHTML = `
                <span class="thinking-dots" aria-hidden="true"><i></i><i></i><i></i></span><span class="thinking-text">Searching your document library…</span>
            `;

            this.container.appendChild(newLoader);
            this.container.scrollTop = this.container.scrollHeight;

            // Premium UX: Cycle through descriptive tasks so the user knows exactly what the sovereign engine is doing
            const legends = [
                "Searching your document library…",
                "Finding relevant passages…",
                "Preparing answer context…",
                "Writing a response locally…"
            ];
            let legendIdx = 0;
            const textEl = newLoader.querySelector('.thinking-text');
            
            // Set initial dynamic legend after 2 seconds
            this.thinkingInterval = setInterval(() => {
                if (textEl) {
                    textEl.style.opacity = '0';
                    setTimeout(() => {
                        textEl.textContent = legends[legendIdx % legends.length];
                        textEl.style.opacity = '1';
                        legendIdx++;
                    }, 200);
                }
            }, 3000);

        } else {
            button.disabled = false;
            button.classList.remove('opacity-80', 'cursor-not-allowed');
            if (input) {
                input.disabled = false;
                input.classList.remove('opacity-80', 'cursor-not-allowed');
                input.focus(); // Auto-focus back on input
            }
            if (btnText) btnText.classList.remove('hidden');
            if (btnSpinner) btnSpinner.classList.add('hidden');
            if (loader) loader.remove();
            
            if (this.thinkingInterval) {
                clearInterval(this.thinkingInterval);
                this.thinkingInterval = null;
            }
        }
    }
}
