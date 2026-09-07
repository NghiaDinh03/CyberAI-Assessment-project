const BACKEND_URL = process.env.API_URL || 'http://backend:8000'

export const dynamic = 'force-dynamic'
export const maxDuration = 1800

export async function GET(request, { params }) {
    try {
        const resolvedParams = params ? await params : {}
        const assessmentId = resolvedParams?.id || params?.id

        if (!assessmentId) {
            return new Response(JSON.stringify({ error: 'Missing assessment ID' }), {
                status: 400,
                headers: { 'Content-Type': 'application/json' }
            })
        }

        const controller = new AbortController()
        const authHeader = request.headers.get('authorization')
        const forwardHeaders = {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
        }
        if (authHeader) {
            forwardHeaders['Authorization'] = authHeader
        }

        const targetUrl = `${BACKEND_URL}/api/iso27001/assessments/${encodeURIComponent(assessmentId)}/stream`
        const res = await fetch(targetUrl, {
            method: 'GET',
            headers: forwardHeaders,
            signal: controller.signal
        })

        if (!res.ok) {
            return new Response(res.body, {
                status: res.status,
                headers: { 'Content-Type': 'application/json' }
            })
        }

        const { readable, writable } = new TransformStream()
        const writer = writable.getWriter()

        // Pipe backend stream to frontend client without buffering
        const pipePromise = (async () => {
            try {
                const reader = res.body.getReader()
                while (true) {
                    const { done, value } = await reader.read()
                    if (done) break
                    try {
                        await writer.write(value)
                    } catch {
                        reader.cancel().catch(() => {})
                        break
                    }
                }
                try { await writer.close() } catch { }
            } catch {
                try { await writer.close() } catch { }
            }
        })()

        request.signal?.addEventListener?.('abort', () => {
            controller.abort()
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
        return new Response(JSON.stringify({ error: err.message || 'Stream connection error' }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
        })
    }
}
