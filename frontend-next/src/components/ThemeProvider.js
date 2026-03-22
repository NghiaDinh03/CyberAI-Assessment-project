'use client'

import { createContext, useContext, useState, useEffect } from 'react'

const ThemeContext = createContext({ theme: 'dark', toggle: () => { } })

export function useTheme() {
    return useContext(ThemeContext)
}

export default function ThemeProvider({ children }) {
    const [theme, setTheme] = useState('dark')
    const [mounted, setMounted] = useState(false)

    useEffect(() => {
        const saved = localStorage.getItem('phobert_theme')
        if (saved === 'light' || saved === 'dark') {
            setTheme(saved)
            document.documentElement.setAttribute('data-theme', saved)
        }
        setMounted(true)
    }, [])

    const toggle = () => {
        const next = theme === 'dark' ? 'light' : 'dark'
        setTheme(next)
        document.documentElement.setAttribute('data-theme', next)
        localStorage.setItem('phobert_theme', next)
    }

    if (!mounted) {
        return <>{children}</>
    }

    return (
        <ThemeContext.Provider value={{ theme, toggle }}>
            {children}
        </ThemeContext.Provider>
    )
}
