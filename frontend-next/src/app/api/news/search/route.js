const BACKEND_URL = process.env.API_URL || 'http://backend:8000'

export async function GET(request) {
    const { searchParams } = new URL(request.url)
    const q = searchParams.get('q') || ''
    const limit = searchParams.get('limit') || '20'

    try {
        const res = await fetch(
            `${BACKEND_URL}/api/news/search?q=${encodeURIComponent(q)}&limit=${limit}`,
            { cache: 'no-store' }
        )

        if (!res.ok) {
            return Response.json(
                { articles: [], count: 0, error: `Backend error: ${res.status}` },
                { status: res.status }
            )
        }

        return Response.json(await res.json())
    } catch (err) {
        return Response.json(
            { articles: [], count: 0, error: err.message },
            { status: 502 }
        )
    }
}
