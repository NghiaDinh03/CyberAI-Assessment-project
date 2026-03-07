const BACKEND_URL = process.env.API_URL || 'http://backend:8000'

export async function GET(request) {
    const { searchParams } = new URL(request.url)
    const category = searchParams.get('category') || 'cybersecurity'
    const limit = searchParams.get('limit') || '15'

    try {
        const res = await fetch(
            `${BACKEND_URL}/api/news?category=${category}&limit=${limit}`,
            { cache: 'no-store' }
        )

        if (!res.ok) {
            return Response.json(
                { articles: [], error: `Backend error: ${res.status}` },
                { status: 200 }
            )
        }

        const data = await res.json()
        return Response.json(data)
    } catch (err) {
        return Response.json(
            { articles: [], error: `Không thể kết nối Backend: ${err.message}` },
            { status: 200 }
        )
    }
}
