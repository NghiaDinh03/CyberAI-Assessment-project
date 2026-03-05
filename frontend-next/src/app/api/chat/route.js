const BACKEND_URL = process.env.API_URL || 'http://backend:8000'

export const maxDuration = 300

export async function POST(request) {
    try {
        const body = await request.json()

        const controller = new AbortController()
        const timeout = setTimeout(() => controller.abort(), 600000)

        const res = await fetch(`${BACKEND_URL}/api/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal: controller.signal
        })

        clearTimeout(timeout)

        if (!res.ok) {
            const errText = await res.text().catch(() => '')
            return Response.json(
                { response: `Backend error: ${res.status}`, error: true },
                { status: res.status }
            )
        }

        return new Response(res.body, {
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
        })
    } catch (err) {
        if (err.name === 'AbortError') {
            return Response.json(
                { response: 'Request timeout (5 phút). Model đang quá tải.', error: true },
                { status: 504 }
            )
        }
        return Response.json(
            { response: `Lỗi kết nối Backend: ${err.message}`, error: true },
            { status: 502 }
        )
    }
}
