'use client'

import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react'
import { translations, defaultLocale, supportedLocales } from '@/i18n'

const STORAGE_KEY = 'language'

const LanguageContext = createContext({
    locale: defaultLocale,
    setLocale: () => {},
    t: (key) => key,
})

export function useTranslation() {
    return useContext(LanguageContext)
}

function getNestedValue(obj, path) {
    return path.split('.').reduce((acc, part) => acc?.[part], obj)
}

export default function LanguageProvider({ children }) {
    const [locale, setLocaleState] = useState(defaultLocale)
    const [mounted, setMounted] = useState(false)

    useEffect(() => {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored && supportedLocales.includes(stored)) {
            setLocaleState(stored)
        }
        setMounted(true)
    }, [])

    const setLocale = useCallback((code) => {
        if (!supportedLocales.includes(code)) return
        setLocaleState(code)
        localStorage.setItem(STORAGE_KEY, code)
        document.documentElement.setAttribute('lang', code)
    }, [])

    const t = useCallback((key, params) => {
        const value = getNestedValue(translations[locale], key)
            ?? getNestedValue(translations[defaultLocale], key)
            ?? key

        if (!params || typeof value !== 'string') return value

        return Object.entries(params).reduce(
            (str, [k, v]) => str.replace(new RegExp(`\\{${k}\\}`, 'g'), v),
            value
        )
    }, [locale])

    const contextValue = useMemo(() => ({
        locale,
        setLocale,
        t,
    }), [locale, setLocale, t])

    if (!mounted) return <>{children}</>

    return (
        <LanguageContext.Provider value={contextValue}>
            {children}
        </LanguageContext.Provider>
    )
}
