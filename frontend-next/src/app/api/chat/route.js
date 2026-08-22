const BACKEND_URL = process.env.API_URL || 'http://backend:8000'

// LocalAI/Ollama on CPU: cold start 1-2 min + inference 3-10 min = up to 30 min worst case
const CONNECT_TIMEOUT_MS = 1800000   // 30 min
const INACTIVITY_TIMEOUT_MS = 1800000 // 30 min inactivity watchdog

export const maxDuration = 1800

export async function POST(request) {
    let controller
    let connectTimer
    try {
        const body = await request.json()

        controller = new AbortController()
        connectTimer = setTimeout(() => controller.abort(), CONNECT_TIMEOUT_MS)

        let res
        try {
            console.log('[api/chat] fwd →', BACKEND_URL, 'model=', body?.model, 'msg_len=', body?.message?.length, 'session=', body?.session_id)
            const authHeader = request.headers.get('authorization')
            const forwardHeaders = { 'Content-Type': 'application/json' }
            if (authHeader) forwardHeaders['Authorization'] = authHeader

            res = await fetch(`${BACKEND_URL}/api/chat/stream`, {
                method: 'POST',
                headers: forwardHeaders,
                body: JSON.stringify(body),
                signal: controller.signal
            })
            console.log('[api/chat] backend status=', res.status)
        } catch (fetchErr) {
            clearTimeout(connectTimer)
            console.error('[api/chat] fwd err:', fetchErr.name, fetchErr.message)
            if (fetchErr.name === 'AbortError') {
                const errorPayload = `data: ${JSON.stringify({ step: 'error', data: { error: true, response: 'Request timed out after 10 minutes. If using LocalAI/Ollama, the model may still be warming up — please try again in a moment.' } })}\n\n`
                return new Response(errorPayload, {
                    headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive' }
                })
            }
            return Response.json(
                { response: `Lỗi kết nối Backend: ${fetchErr.message}`, error: true },
                { status: 502 }
            )
        }

        clearTimeout(connectTimer)

        if (!res.ok) {
            const errBody = await res.text().catch(() => '')
            let detail = `Backend error: ${res.status}`
            try {
                const parsed = JSON.parse(errBody)
                if (Array.isArray(parsed.detail)) {
                    // Pydantic validation errors — extract human-readable messages
                    detail = parsed.detail.map(e => e.msg || e.message || JSON.stringify(e)).join('; ')
                } else if (typeof parsed.detail === 'string') {
                    detail = parsed.detail
                } else if (parsed.detail) {
                    detail = JSON.stringify(parsed.detail)
                }
            } catch { }
            // Return as SSE error so frontend can handle it gracefully
            const errorPayload = `data: ${JSON.stringify({ step: 'error', data: { error: true, response: detail } })}\n\n`
            return new Response(errorPayload, {
                headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive' }
            })
        }

        const { readable, writable } = new TransformStream()
        const writer = writable.getWriter()

        let inactivityTimer = setTimeout(() => {
            const msg = `data: ${JSON.stringify({ step: 'error', data: { error: true, response: 'Stream inactive for 30 minutes. Please try again.' } })}\n\n`
            writer.write(new TextEncoder().encode(msg)).then(() => writer.close()).catch(() => {})
        }, INACTIVITY_TIMEOUT_MS)

        // Pipe backend SSE → client in background
        const pipePromise = (async () => {
            try {
                const reader = res.body.getReader()
                while (true) {
                    const { done, value } = await reader.read()
                    if (done) break

                    // Reset inactivity timer on each chunk
                    clearTimeout(inactivityTimer)
                    inactivityTimer = setTimeout(() => {
                        const msg = `data: ${JSON.stringify({ step: 'error', data: { error: true, response: 'Stream inactive for 30 minutes. Please try again.' } })}\n\n`
                        writer.write(new TextEncoder().encode(msg)).then(() => writer.close()).catch(() => {})
                    }, INACTIVITY_TIMEOUT_MS)

                    try {
                        await writer.write(value)
                    } catch {
                        // Client disconnected — stop reading
                        reader.cancel().catch(() => {})
                        break
                    }
                }
                clearTimeout(inactivityTimer)
                try { await writer.close() } catch { }
            } catch {
                clearTimeout(inactivityTimer)
                try { await writer.close() } catch { }
            }
        })()

        // Ensure cleanup when client aborts the request
        request.signal?.addEventListener?.('abort', () => {
            clearTimeout(inactivityTimer)
            pipePromise.then(() => {}).catch(() => {})
            try { writer.close() } catch { }
        })

        return new Response(readable, {
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache, no-transform',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            }
        })
    } catch (err) {
        if (connectTimer) clearTimeout(connectTimer)
        // Return as SSE error format so frontend always gets a parseable response
        const errorPayload = `data: ${JSON.stringify({ step: 'error', data: { error: true, response: `Lỗi kết nối Backend: ${err.message}` } })}\n\n`
        return new Response(errorPayload, {
            headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive' }
        })
    }
}
