/**
 * Zyrabit System Constants
 * Centralized registry for events and element IDs to ensure strictness.
 */

export const EVENTS = {
    CHAT: {
        SEND: 'CHAT:SEND',
        RESPONSE_RECEIVED: 'CHAT:RESPONSE_RECEIVED'
    },
    UI: {
        MSG_ADDED: 'UI:MSG_ADDED',
        THINKING: 'UI:THINKING'
    },
    SOCKET: {
        EMIT: 'SOCKET:EMIT'
    },
    SYSTEM: {
        LOG: 'SYSTEM:LOG'
    }
};

export const IDS = {
    CHAT_FORM: 'chat-form',
    CHAT_INPUT: 'chat-input',
    CHAT_CONTAINER: 'chat-container',
    CHAT_SUBMIT: 'chat-submit',
    VAULT_BTN: 'input-vault-btn',
    TOGGLE_GDPR: 'toggle-gdpr',
    TOGGLE_INGEST: 'toggle-ingest',
    CLOSE_GDPR: 'close-gdpr',
    CLOSE_INGEST: 'close-ingest',
    GDPR_PANEL: 'gdpr-panel',
    INGEST_PANEL: 'ingest-panel',
    DOCS_PANEL: 'docs-panel',
    DROP_ZONE: 'drop-zone',
    FILE_INPUT: 'file-input',
    GDPR_LOGS: 'gdpr-logs'
};
