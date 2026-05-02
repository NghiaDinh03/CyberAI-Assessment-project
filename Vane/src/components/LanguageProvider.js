'use client'

import { createContext, useContext, useState, useCallback, useEffect } from 'react'

const LANG_KEY = 'cyberai_lang'

const LangContext = createContext({
    locale: 'en',
    setLocale: () => {},
    t: (key) => key,
})

export function useTranslation() {
    return useContext(LangContext)
}

function resolveNested(obj, path) {
    return path.split('.').reduce((acc, part) => (acc && acc[part] !== undefined ? acc[part] : null), obj)
}

export default function LanguageProvider({ children }) {
    const [locale, setLocaleState] = useState('en')
    const [dict, setDict] = useState({})

    useEffect(() => {
        const saved = typeof window !== 'undefined' ? localStorage.getItem(LANG_KEY) : null
        const lang = saved || 'en'
        setLocaleState(lang)
        import(`../i18n/${lang}.json`).then(m => setDict(m.default || m)).catch(() => {})
    }, [])

    const setLocale = useCallback((code) => {
        setLocaleState(code)
        localStorage.setItem(LANG_KEY, code)
        import(`../i18n/${code}.json`).then(m => setDict(m.default || m)).catch(() => {})
    }, [])

    const t = useCallback((key, vars) => {
        let val = resolveNested(dict, key)
        if (val == null) return key
        if (vars) {
            Object.entries(vars).forEach(([k, v]) => {
                val = val.replace(`{${k}}`, v)
            })
        }
        return val
    }, [dict])

    return (
        <LangContext.Provider value={{ locale, setLocale, t }}>
            {children}
        </LangContext.Provider>
    )
}
