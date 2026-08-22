import { NextResponse } from 'next/server'

const BACKEND_URL = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000'

export async function GET() {
    try {
        const res = await fetch(`${BACKEND_URL}/openapi.json`, {
            cache: 'no-store',
            headers: { 'Accept': 'application/json' }
        })
        if (!res.ok) {
            return NextResponse.json({ error: 'Failed to fetch backend openapi schema' }, { status: res.status })
        }
        const data = await res.json()
        return NextResponse.json(data)
    } catch (err) {
        return NextResponse.json({ error: err.message }, { status: 500 })
    }
}
