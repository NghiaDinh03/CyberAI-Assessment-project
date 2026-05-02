'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useTheme } from './ThemeProvider'
import { useTranslation } from './LanguageProvider'
import styles from './Navbar.module.css'
import { Home, MessageSquare, Shield, BookOpen, BarChart2, Sun, Moon, Settings } from 'lucide-react'

const NAV_ITEMS = [
    { href: '/', labelKey: 'nav.home', icon: Home },
    { href: '/chatbot', labelKey: 'nav.aiChat', icon: MessageSquare },
    { href: '/form-iso', labelKey: 'nav.assessment', icon: Shield },
    { href: '/standards', labelKey: 'nav.standards', icon: BookOpen },
    { href: '/analytics', labelKey: 'nav.analytics', icon: BarChart2 },
]

const TIMEZONES = [
    { label: 'VN', value: 'Asia/Ho_Chi_Minh' },
    { label: 'US', value: 'America/Los_Angeles' },
    { label: 'UTC', value: 'UTC' },
]

export default function Navbar() {
    const pathname = usePathname()
    const { theme, toggle } = useTheme()
    const { t, locale } = useTranslation()
    const [time, setTime] = useState('')
    const [date, setDate] = useState('')
    const [tzIdx, setTzIdx] = useState(0)
    const [mounted, setMounted] = useState(false)
    const [mobileOpen, setMobileOpen] = useState(false)

    useEffect(() => { setMounted(true) }, [])

    const handleTzClick = () => {
        setTzIdx(prev => (prev + 1) % TIMEZONES.length)
    }

    const formatTime = (date, timezone) => {
        const fmt = locale === 'vi' ? 'vi-VN' : 'en-US'
        const timeStr = date.toLocaleTimeString(fmt, {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            timeZone: timezone,
            hour12: false
        })
        const dateStr = date.toLocaleDateString(fmt, {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            timeZone: timezone
        })
        return { timeStr, dateStr }
    }

    useEffect(() => {
        const update = () => {
            const { timeStr, dateStr } = formatTime(new Date(), TIMEZONES[tzIdx].value)
            setTime(timeStr)
            setDate(dateStr)
        }
        update()
        const id = setInterval(update, 1000)
        return () => clearInterval(id)
    }, [tzIdx, locale])

    useEffect(() => {
        setMobileOpen(false)
    }, [pathname])

    return (
        <>
        {mobileOpen && <div className={styles.navBackdrop} onClick={() => setMobileOpen(false)} aria-hidden="true" />}
        <nav className={styles.navbar}>
            <div className={styles.inner}>
                <Link href="/" className={styles.brand}>
                    <svg className={styles.brandIcon} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                        <path d="M16 3L4 8v8c0 6.627 5.153 12.417 12 13.95C22.847 28.417 28 22.627 28 16V8L16 3z" fill="currentColor" opacity="0.15"/>
                        <path d="M16 3L4 8v8c0 6.627 5.153 12.417 12 13.95C22.847 28.417 28 22.627 28 16V8L16 3z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/>
                        <path d="M11 16l3.5 3.5L21 12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    <span className={styles.brandText}>{t('common.appName')}</span>
                </Link>

                <button
                    className={styles.hamburger}
                    onClick={() => setMobileOpen(!mobileOpen)}
                    aria-label={t('nav.toggleMenu')}
                    aria-expanded={mobileOpen}
                >
                    <span className={`${styles.hamburgerLine} ${mobileOpen ? styles.hamburgerOpen : ''}`} />
                </button>

                <div className={`${styles.navLinks} ${mobileOpen ? styles.navLinksOpen : ''}`} role="navigation">
                    {NAV_ITEMS.map(item => (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`${styles.navLink} ${pathname === item.href ? styles.navLinkActive : ''}`}
                        >
                            <item.icon size={15} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
                            {t(item.labelKey)}
                        </Link>
                    ))}
                </div>

                <div className={styles.controls}>
                    <div className={styles.clock} onClick={handleTzClick} title={t('nav.clickTimezone')}>
                        <span className={styles.clockTime}>{mounted ? time : '--:--:--'}</span>
                        <span className={styles.clockMeta}>
                            {mounted ? date : '--/--/----'} · {TIMEZONES[tzIdx].label}
                        </span>
                    </div>

                    <div className={styles.statusDot} title={t('nav.backendOnline')}>
                        <span className={styles.dot} />
                    </div>

                    {mounted && (
                        <>
                        <Link
                            href="/settings"
                            className={styles.settingsBtn}
                            aria-label={t('nav.settings')}
                            title={t('nav.settings')}
                        >
                            <Settings size={16} strokeWidth={1.8} />
                        </Link>
                        <button
                            className={styles.themeToggle}
                            onClick={toggle}
                            aria-label={theme === 'dark' ? t('nav.switchToLight') : t('nav.switchToDark')}
                            title={theme === 'dark' ? t('nav.switchToLight') : t('nav.switchToDark')}
                        >
                            {theme === 'dark'
                                ? <Sun size={16} strokeWidth={1.8} />
                                : <Moon size={16} strokeWidth={1.8} />}
                        </button>
                        </>
                    )}
                </div>
            </div>
        </nav>
        </>
    )
}
