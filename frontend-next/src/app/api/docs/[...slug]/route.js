import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

const DOCS_DIR = path.join(process.cwd(), 'docs')

export async function GET(request, context) {
    const { slug } = await context.params
    if (!slug || slug.length < 2) {
        return NextResponse.json({ error: 'Invalid path' }, { status: 400 })
    }

    const lang = slug[0]
    const filename = slug.slice(1).join('/')

    if (!['en', 'vi'].includes(lang)) {
        return NextResponse.json({ error: 'Invalid language' }, { status: 400 })
    }

    if (filename.includes('..') || filename.includes('\\')) {
        return NextResponse.json({ error: 'Invalid path' }, { status: 400 })
    }

    const filePath = path.join(DOCS_DIR, lang, filename)
    const fallbackPath = lang !== 'en' ? path.join(DOCS_DIR, 'en', filename) : null

    try {
        if (fs.existsSync(filePath)) {
            const content = fs.readFileSync(filePath, 'utf-8')
            return new NextResponse(content, {
                headers: {
                    'Content-Type': 'text/plain; charset=utf-8',
                    'Cache-Control': 'public, max-age=3600',
                }
            })
        }

        if (fallbackPath && fs.existsSync(fallbackPath)) {
            const content = fs.readFileSync(fallbackPath, 'utf-8')
            return new NextResponse(content, {
                headers: {
                    'Content-Type': 'text/plain; charset=utf-8',
                    'Cache-Control': 'public, max-age=3600',
                }
            })
        }

        return NextResponse.json({ error: 'Document not found' }, { status: 404 })
    } catch (e) {
        return NextResponse.json({ error: 'Failed to read document' }, { status: 500 })
    }
}
