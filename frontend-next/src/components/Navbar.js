'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useTheme } from './ThemeProvider'
import styles from './Navbar.module.css'

const NAV_ITEMS = [
    { href: '/', label: 'Home' },
    { href: '/chatbot', label: 'AI Chat' },
    { href: '/form-iso', label: 'Assessment' },
    { href: '/standards', label: 'Standards' },
    { href: '/analytics', label: 'Analytics' },
]

const TIMEZONES = [
    { label: 'VN', value: 'Asia/Ho_Chi_Minh' },
    { label: 'US', value: 'America/Los_Angeles' },
    { label: 'UTC', value: 'UTC' },
]

export default function Navbar() {
    const pathname = usePathname()
    const { theme, toggle } = useTheme()
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
        const timeStr = date.toLocaleTimeString('vi-VN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            timeZone: timezone,
            hour12: false
        })
        const dateStr = date.toLocaleDateString('vi-VN', {
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
    }, [tzIdx])

    useEffect(() => {
        setMobileOpen(false)
    }, [pathname])

    return (
        <>
        {mobileOpen && <div className={styles.navBackdrop} onClick={() => setMobileOpen(false)} aria-hidden="true" />}
        <nav className={styles.navbar}>
            <div className={styles.inner}>
                <Link href="/" className={styles.brand}>
                    <span className={styles.brandMark}>CA</span>
                    <span className={styles.brandText}>CyberAI</span>
                </Link>

                <button
                    className={styles.hamburger}
                    onClick={() => setMobileOpen(!mobileOpen)}
                    aria-label="Toggle menu"
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
                            {item.label}
                        </Link>
                    ))}
                </div>

                <div className={styles.controls}>
                    <div className={styles.clock} onClick={handleTzClick} title="Click to switch timezone">
                        <span className={styles.clockTime}>{mounted ? time : '--:--:--'}</span>
                        <span className={styles.clockMeta}>
                            {mounted ? date : '--/--/----'} · {TIMEZONES[tzIdx].label}
                        </span>
                    </div>

                    <div className={styles.statusDot} title="Backend Online">
                        <span className={styles.dot} />
                    </div>

                    {mounted && (
                        <button
                            className={styles.themeToggle}
                            onClick={toggle}
                            aria-label="Toggle theme"
                            title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                        >
                            <span className={styles.themeLabel}>
                                {theme === 'dark' ? 'Light' : 'Dark'}
                            </span>
                        </button>
                    )}
                </div>
            </div>
        </nav>
        </>
    )
}
