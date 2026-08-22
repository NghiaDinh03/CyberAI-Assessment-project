/**
 * Dynamic Control Descriptions Module
 * Control descriptions are stored and served dynamically via SQLite Database (GET /api/standards/control-descriptions).
 * This module provides dynamic hooks and cached access.
 */

let cachedDescriptions = { vi: null, en: null }

export async function fetchControlDescriptionsFromAPI(locale = 'vi') {
    if (cachedDescriptions[locale]) {
        return cachedDescriptions[locale]
    }
    try {
        const res = await fetch(`/api/standards/control-descriptions?locale=${locale}`)
        if (res.ok) {
            const data = await res.json()
            if (data.descriptions) {
                cachedDescriptions[locale] = data.descriptions
                return data.descriptions
            }
        }
    } catch (e) {
        console.error('Failed to fetch control descriptions from backend:', e)
    }
    return cachedDescriptions[locale] || {}
}

export function getControlDescriptions(locale = 'vi') {
    return cachedDescriptions[locale] || {}
}

export const CONTROL_DESCRIPTIONS = {}
