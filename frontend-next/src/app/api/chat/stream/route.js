import { POST as chatHandler } from '../route'

export const dynamic = 'force-dynamic'
export const maxDuration = 1800

export async function POST(request) {
    return chatHandler(request)
}
