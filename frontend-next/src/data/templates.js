import { ASSESSMENT_TEMPLATES_VI } from './templates.vi'
import { ASSESSMENT_TEMPLATES_EN } from './templates.en'

export const ASSESSMENT_TEMPLATES_BY_LOCALE = { vi: ASSESSMENT_TEMPLATES_VI, en: ASSESSMENT_TEMPLATES_EN }

export function getAssessmentTemplates(locale = 'vi') {
    return ASSESSMENT_TEMPLATES_BY_LOCALE[locale] || ASSESSMENT_TEMPLATES_VI
}

// Backward-compat default export
export const ASSESSMENT_TEMPLATES = ASSESSMENT_TEMPLATES_VI
