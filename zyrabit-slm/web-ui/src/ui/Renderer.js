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
        bus.on(EVENTS.UI.MSG_ADDED, (data) => this.renderMessage(data.role, data.text, data.metadata));
        bus.on(EVENTS.UI.THINKING, (state) => this.toggleThinking(state));
    }


    renderMessage(role, text, metadata = null) {
        const now = new Date();
        const dateStr = now.toLocaleDateString([], { weekday: 'long', day: 'numeric', month: 'long' });
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // Add Date Separator if needed
        if (this.lastDate !== dateStr) {
            const separator = document.createElement('div');
            separator.className = 'date-separator';
            separator.innerHTML = `<span class="date-pill">${dateStr}</span>`;
            this.container.appendChild(separator);
            this.lastDate = dateStr;
        }

        const msg = document.createElement('zyra-chat-message');
        msg.data = { role, text, metadata, timestamp: timeStr };
        
        this.container.appendChild(msg);
        
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
        if (!button) return;

        const btnText = button.querySelector('.button-text');
        const btnSpinner = button.querySelector('.loader-spin');

        if (state) {
            button.disabled = true;
            button.classList.add('opacity-80', 'cursor-not-allowed');
            if (btnText) btnText.classList.add('hidden');
            if (btnSpinner) btnSpinner.classList.remove('hidden');
            
            if (loader) return;

            const newLoader = document.createElement('div');
            newLoader.id = 'thinking-bubble';
            newLoader.className = 'flex justify-start animate-in fade-in slide-in-from-bottom-2 duration-300';
            newLoader.innerHTML = `
                <div class="flex items-start gap-3 max-w-[85%]">
                    <div class="w-8 h-8 rounded-full bg-zyrabit-surface border border-zyrabit-border flex items-center justify-center flex-shrink-0">
                        <img src="/img/logo.png" class="w-5 h-5 object-contain animate-pulse">
                    </div>
                    <div class="bg-zyrabit-surface p-4 rounded-2xl rounded-tl-none text-sm text-zyrabit-primary italic flex items-center gap-2 border border-zyrabit-border/30">
                        <span class="animate-pulse">Zyra is thinking...</span>
                    </div>
                </div>
            `;
            this.container.appendChild(newLoader);
            this.container.scrollTop = this.container.scrollHeight;
        } else {
            button.disabled = false;
            button.classList.remove('opacity-80', 'cursor-not-allowed');
            if (btnText) btnText.classList.remove('hidden');
            if (btnSpinner) btnSpinner.classList.add('hidden');
            if (loader) loader.remove();
        }
    }
}
