import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.API_URL || 'http://backend:8000';

export async function GET(request) {
    const { searchParams } = new URL(request.url);
    const category = searchParams.get('category') || 'all';

    try {
        const res = await fetch(
            `${BACKEND_URL}/api/news/history?category=${category}`,
            { cache: 'no-store' }
        );

        if (!res.ok) {
            return NextResponse.json(
                { history: [], error: `Backend error: ${res.status}` },
                { status: 200 }
            );
        }

        const data = await res.json();
        return NextResponse.json(data);
    } catch (err) {
        return NextResponse.json(
            { history: [], error: `Không thể kết nối Backend: ${err.message}` },
            { status: 200 }
        );
    }
}
