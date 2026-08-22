const BACKEND_URL = process.env.API_URL || 'http://backend:8000'

export async function GET(request, { params }) {
    try {
        const resolvedParams = await params
        const slug = resolvedParams?.slug ? (Array.isArray(resolvedParams.slug) ? resolvedParams.slug.join('/') : resolvedParams.slug) : ''
        const url = new URL(request.url)
        const search = url.search

        const targetUrl = `${BACKEND_URL}/api/system/${slug}${search}`

        const res = await fetch(targetUrl, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                ...(request.headers.get('authorization') ? { 'Authorization': request.headers.get('authorization') } : {}),
            },
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
        return Response.json({ detail: `Lỗi kết nối máy chủ hệ thống: ${err.message}` }, { status: 502 })
    }
}
