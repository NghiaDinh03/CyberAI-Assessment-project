const BACKEND_URL = process.env.API_URL || 'http://backend:8000'

export async function GET(request) {
    const { searchParams } = new URL(request.url)
    const category = searchParams.get('category') || 'cybersecurity'
    const limit = searchParams.get('limit') || '15'

    try {
        const res = await fetch(
            `${BACKEND_URL}/api/news?category=${category}&limit=${limit}`,
            { next: { revalidate: 300 } }
        )

        if (!res.ok) {
            return Response.json(
                { articles: [], error: `Backend error: ${res.status}` },
                { status: res.status }
            )
        }

        const data = await res.json()
        return Response.json(data)
    } catch (err) {
        return Response.json(
            { articles: [], error: err.message },
            { status: 502 }
        )
    }
}
