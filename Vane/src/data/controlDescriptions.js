export { CONTROL_DESCRIPTIONS as CONTROL_DESCRIPTIONS_VI } from './controlDescriptions.vi'
import { CONTROL_DESCRIPTIONS as VI } from './controlDescriptions.vi'
import { CONTROL_DESCRIPTIONS_EN as EN } from './controlDescriptions.en'

export const CONTROL_DESCRIPTIONS_BY_LOCALE = { vi: VI, en: EN }

export function getControlDescriptions(locale = 'vi') {
    return CONTROL_DESCRIPTIONS_BY_LOCALE[locale] || VI
}

// Backward-compat default export (defaults to Vietnamese for legacy imports)
export const CONTROL_DESCRIPTIONS = VI
