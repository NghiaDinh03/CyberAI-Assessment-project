'use client'

import { useState, useEffect, useMemo } from 'react'
import { useTranslation } from '@/components/LanguageProvider'
import { getAssessmentTemplates, BUILTIN_TEMPLATES } from './templates'
import { fetchControlDescriptionsFromAPI } from './controlDescriptions'
import { getStandardsByLocale } from './standards'

/** Return the assessment templates list for the current UI locale. */
export function useAssessmentTemplates() {
    const { locale } = useTranslation()
    return useMemo(() => getAssessmentTemplates(locale), [locale])
}

/** Return the control descriptions map dynamically from backend SQLite database. */
export function useControlDescriptions() {
    const { locale } = useTranslation()
    const [descriptions, setDescriptions] = useState({})

    useEffect(() => {
        let isMounted = true
        fetchControlDescriptionsFromAPI(locale).then(data => {
            if (isMounted && data && Object.keys(data).length > 0) {
                setDescriptions(data)
            }
        })
        return () => { isMounted = false }
    }, [locale])

    return descriptions
}

/** Return the assessment standards list for the current UI locale. */
export function useAssessmentStandards() {
    const { locale } = useTranslation()
    return useMemo(() => getStandardsByLocale(locale), [locale])
}

export {
    getAssessmentTemplates,
    getStandardsByLocale,
    BUILTIN_TEMPLATES,
}
