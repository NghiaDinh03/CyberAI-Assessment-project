const BACKEND_URL = process.env.API_URL || 'http://backend:8000'

export async function POST(request) {
    try {
        const body = await request.json()
        const res = await fetch(`${BACKEND_URL}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            cache: 'no-store',
        })
        const text = await res.text()
        try {
            const data = JSON.parse(text)
            return Response.json(data, { status: res.status })
        } catch (_) {
            return new Response(text, { status: res.status, headers: { 'Content-Type': 'application/json' } })
        }
    } catch (err) {
        return Response.json({ detail: `Lỗi kết nối máy chủ xác thực: ${err.message}` }, { status: 502 })
    }
}
