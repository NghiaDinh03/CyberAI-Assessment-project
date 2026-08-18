'use client'

import { useMemo } from 'react'
import { useTranslation } from '@/components/LanguageProvider'
import { getAssessmentTemplates, ASSESSMENT_TEMPLATES_BY_LOCALE } from './templates'
import { getControlDescriptions, CONTROL_DESCRIPTIONS_BY_LOCALE } from './controlDescriptions'
import { getStandardsByLocale } from './standards'

/** Return the assessment templates list for the current UI locale. */
export function useAssessmentTemplates() {
    const { locale } = useTranslation()
    return useMemo(() => getAssessmentTemplates(locale), [locale])
}

/** Return the control descriptions map for the current UI locale. */
export function useControlDescriptions() {
    const { locale } = useTranslation()
    return useMemo(() => getControlDescriptions(locale), [locale])
}

/** Return the assessment standards list for the current UI locale. */
export function useAssessmentStandards() {
    const { locale } = useTranslation()
    return useMemo(() => getStandardsByLocale(locale), [locale])
}

export {
    getAssessmentTemplates,
    getControlDescriptions,
    getStandardsByLocale,
    ASSESSMENT_TEMPLATES_BY_LOCALE,
    CONTROL_DESCRIPTIONS_BY_LOCALE,
}

