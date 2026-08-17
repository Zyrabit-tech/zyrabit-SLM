export async function sendChat({ text, client_msg_id = null, history = null, provider = null, session_id = null, document_id = null } = {}) {
    const res = await fetch('/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, client_msg_id, history, provider, session_id, document_id })
    });
    if (!res.ok) throw new Error(`HTTP_${res.status}`);
    return res.json();
}

export async function queryNode({ text, session_id = 'default', document_id = null } = {}) {
    const res = await fetch('/v1/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, session_id, document_id })
    });
    if (!res.ok) throw new Error(`HTTP_${res.status}`);
    return res.json();
}

export async function deleteSession(sessionId) {
    try {
        const res = await fetch(`/v1/sessions/${sessionId}`, { method: 'DELETE' });
        return res;
    } catch (err) {
        // Let callers decide how to handle network errors; return a falsy value on failure
        return null;
    }
}

export default {
    sendChat,
    queryNode,
    deleteSession
};

export async function getSession(sessionId) {
    const res = await fetch(`/v1/sessions/${sessionId}`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP_${res.status}`);
    return res.json();
}

export async function getProfile() {
    const res = await fetch('/v1/profile');
    if (!res.ok) throw new Error(`HTTP_${res.status}`);
    return res.json();
}

export async function saveProfile(profile) {
    const res = await fetch('/v1/profile', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile)
    });
    if (!res.ok) throw new Error(`HTTP_${res.status}`);
    return res.json();
}

export async function patchSessionContext(sessionId, payload) {
    const res = await fetch(`/v1/sessions/${sessionId}/context`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`HTTP_${res.status}`);
    return res.json();
}

export async function getHealth() {
    const res = await fetch('/v1/health');
    if (!res.ok) throw new Error(`HTTP_${res.status}`);
    return res.json();
}

export async function getDocuments() {
    const res = await fetch('/v1/documents', { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP_${res.status}`);
    return res.json();
}

export async function getTools() {
    const res = await fetch('/v1/tools');
    if (!res.ok) throw new Error(`HTTP_${res.status}`);
    return res.json();
}

export async function importSource(formData) {
    const res = await fetch('/v1/sources/import', { method: 'POST', body: formData });
    if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(payload.detail || `The import request was rejected (HTTP ${res.status}).`);
    }
    return res.json();
}

export async function getJob(jobId) {
    const res = await fetch(`/v1/jobs/${jobId}`);
    if (!res.ok) throw new Error('Job status unavailable');
    return res.json();
}
