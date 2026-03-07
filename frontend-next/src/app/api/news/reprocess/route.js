import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.API_URL || 'http://backend:8000';

export async function POST(request) {
    try {
        const body = await request.json();
        const { url } = body;

        const res = await fetch(`${BACKEND_URL}/api/news/reprocess`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url }),
        });

        const data = await res.json();
        if (!res.ok) {
            return NextResponse.json(
                { error: data.detail || `Backend error: ${res.status}` },
                { status: 400 }
            );
        }

        return NextResponse.json(data);
    } catch (err) {
        return NextResponse.json(
            { error: `Không thể kết nối Backend: ${err.message}` },
            { status: 500 }
        );
    }
}
