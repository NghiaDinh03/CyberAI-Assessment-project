const API_BASE = typeof window !== 'undefined'
    ? ''
    : (process.env.API_URL || 'http://backend:8000');

export async function fetchSystemStats() {
    const res = await fetch(`${API_BASE}/api/system/stats`, {
        cache: 'no-store'
    });
    if (!res.ok) throw new Error('Failed to fetch system stats');
    return res.json();
}

export async function fetchServiceStatus() {
    try {
        const healthRes = await fetch(`${API_BASE}/api/health`, { cache: 'no-store' });
        const backendReady = healthRes.ok;

        return {
            backend: {
                status: backendReady ? 'Running' : 'Offline',
                ready: backendReady
            }
        };
    } catch {
        return {
            backend: { status: 'Offline', ready: false }
        };
    }
}

export async function sendChatMessage(message, sessionId) {
    const res = await fetch(`/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: sessionId })
    });

    if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Backend error (${res.status}): ${errorText}`);
    }

    return res.json();
}

export async function getSystemStatsClient() {
    const res = await fetch('/api/system/stats');
    if (!res.ok) throw new Error('Failed to fetch');
    return res.json();
}

// ── Evidence URL helpers (Step 5) ─────────────────────────────────────
// Matches backend routes in backend/api/routes/iso27001.py:
//   GET /api/iso27001/evidence/{control_id}/{filename}           → raw file
//   GET /api/iso27001/evidence/{control_id}/{filename}/preview   → JSON preview
export function getEvidenceDownloadUrl(controlId, filename) {
    if (!controlId || !filename) return ''
    return `/api/iso27001/evidence/${encodeURIComponent(controlId)}/${encodeURIComponent(filename)}`
}

export function getEvidencePreviewUrl(controlId, filename) {
    if (!controlId || !filename) return ''
    return `/api/iso27001/evidence/${encodeURIComponent(controlId)}/${encodeURIComponent(filename)}/preview`
}

// ── Template Evidence helpers ─────────────────────────────────────────
export async function uploadTemplateEvidence(templateId, file) {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`/api/templates/${encodeURIComponent(templateId)}/evidence/upload`, {
        method: 'POST',
        body: form,
    })
    if (!res.ok) {
        const txt = await res.text()
        throw new Error(`Upload failed (${res.status}): ${txt}`)
    }
    return res.json()
}

export async function getTemplateEvidence(templateId) {
    const res = await fetch(`/api/templates/${encodeURIComponent(templateId)}/evidence`)
    if (!res.ok) throw new Error(`Failed to fetch evidence (${res.status})`)
    return res.json()
}

export function getTemplateEvidenceRawUrl(templateId, docId) {
    if (!templateId || !docId) return ''
    return `/api/templates/${encodeURIComponent(templateId)}/evidence/${encodeURIComponent(docId)}/raw`
}

export function getTemplateEvidenceTextUrl(templateId, docId) {
    if (!templateId || !docId) return ''
    return `/api/templates/${encodeURIComponent(templateId)}/evidence/${encodeURIComponent(docId)}/text`
}
