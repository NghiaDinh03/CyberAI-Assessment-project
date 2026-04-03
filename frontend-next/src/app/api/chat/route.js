const BACKEND_URL = process.env.API_URL || 'http://backend:8000'

export const maxDuration = 300

export async function POST(request) {
    try {
        const body = await request.json()

        const controller = new AbortController()
        // 120s hard timeout — streams an error event then closes
        const timeout = setTimeout(() => controller.abort(), 120000)

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
                // Stream a user-visible timeout error as SSE then close
                const errorPayload = `data: ${JSON.stringify({ step: 'error', data: { error: true, response: 'Request timed out after 120 seconds. The model is overloaded — please try again.' } })}\n\n`
                return new Response(errorPayload, {
                    headers: {
                        'Content-Type': 'text/event-stream',
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive'
                    }
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

        // Pipe backend SSE stream directly to client, but wrap it so we can
        // inject a timeout error if the stream stalls after the initial connect.
        const { readable, writable } = new TransformStream()
        const writer = writable.getWriter()
        const encoder = new TextEncoder()

        // 120s inactivity watchdog on the piped stream
        let streamTimeout = setTimeout(async () => {
            try {
                const msg = `data: ${JSON.stringify({ step: 'error', data: { error: true, response: 'Stream timed out after 120 seconds. Please try again.' } })}\n\n`
                await writer.write(encoder.encode(msg))
                await writer.close()
            } catch { }
        }, 120000)

        ;(async () => {
            try {
                const reader = res.body.getReader()
                while (true) {
                    const { done, value } = await reader.read()
                    if (done) break
                    clearTimeout(streamTimeout)
                    streamTimeout = setTimeout(async () => {
                        try {
                            const msg = `data: ${JSON.stringify({ step: 'error', data: { error: true, response: 'Stream timed out after 120 seconds. Please try again.' } })}\n\n`
                            await writer.write(encoder.encode(msg))
                            await writer.close()
                        } catch { }
                    }, 120000)
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
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
        })
    } catch (err) {
        return Response.json(
            { response: `Lỗi kết nối Backend: ${err.message}`, error: true },
            { status: 502 }
        )
    }
}
