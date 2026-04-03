const BACKEND_URL = process.env.API_URL || 'http://backend:8000'

// LocalAI cold start (loading ~5GB GGUF into RAM) can take 3-5 minutes
const CONNECT_TIMEOUT_MS = 300000   // 5 min — allows LocalAI model warmup
const INACTIVITY_TIMEOUT_MS = 300000 // 5 min — inactivity watchdog

export const maxDuration = 300

export async function POST(request) {
    try {
        const body = await request.json()

        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), CONNECT_TIMEOUT_MS)

        let res
        try {
            res = await fetch(`${BACKEND_URL}/api/chat/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: controller.signal
            })
        } catch (fetchErr) {
            clearTimeout(timeout)
            if (fetchErr.name === 'AbortError') {
                const errorPayload = `data: ${JSON.stringify({ step: 'error', data: { error: true, response: 'Request timed out after 5 minutes. If using LocalAI, the model may still be warming up — please try again in a moment.' } })}\n\n`
                return new Response(errorPayload, {
                    headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive' }
                })
            }
            return Response.json(
                { response: `Lỗi kết nối Backend: ${fetchErr.message}`, error: true },
                { status: 502 }
            )
        }

        clearTimeout(timeout)

        if (!res.ok) {
            await res.text().catch(() => '')
            return Response.json(
                { response: `Backend error: ${res.status}`, error: true },
                { status: res.status }
            )
        }

        const { readable, writable } = new TransformStream()
        const writer = writable.getWriter()
        const encoder = new TextEncoder()

        let streamTimeout = setTimeout(async () => {
            try {
                const msg = `data: ${JSON.stringify({ step: 'error', data: { error: true, response: 'Stream inactive for 5 minutes. Please try again.' } })}\n\n`
                await writer.write(encoder.encode(msg))
                await writer.close()
            } catch { }
        }, INACTIVITY_TIMEOUT_MS)

        ;(async () => {
            try {
                const reader = res.body.getReader()
                while (true) {
                    const { done, value } = await reader.read()
                    if (done) break
                    clearTimeout(streamTimeout)
                    streamTimeout = setTimeout(async () => {
                        try {
                            const msg = `data: ${JSON.stringify({ step: 'error', data: { error: true, response: 'Stream inactive for 5 minutes. Please try again.' } })}\n\n`
                            await writer.write(encoder.encode(msg))
                            await writer.close()
                        } catch { }
                    }, INACTIVITY_TIMEOUT_MS)
                    await writer.write(value)
                }
                clearTimeout(streamTimeout)
                await writer.close()
            } catch {
                clearTimeout(streamTimeout)
                try { await writer.abort() } catch { }
            }
        })()

        return new Response(readable, {
            headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive' }
        })
    } catch (err) {
        return Response.json(
            { response: `Lỗi kết nối Backend: ${err.message}`, error: true },
            { status: 502 }
        )
    }
}
