'use client'

import { useState, useEffect } from 'react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import styles from './Navbar.module.css'

const NAV_ITEMS = [
    { href: '/', label: 'Trang chủ', icon: '🏠' },
    { href: '/chatbot', label: 'AI Chat', icon: '💬' },
    { href: '/analytics', label: 'Analytics', icon: '📊' },
    { href: '/form-iso', label: 'Form ISO', icon: '📋' },
    { href: '/templates', label: 'Kho Mẫu', icon: '📂' },
    { href: '/news', label: 'Tin tức', icon: '📰' }
]

const TIMEZONES = [
    { label: 'VN', zone: 'Asia/Ho_Chi_Minh' },
    { label: 'UTC', zone: 'UTC' },
    { label: 'US', zone: 'America/New_York' },
    { label: 'JP', zone: 'Asia/Tokyo' }
]

export default function Navbar() {
    const pathname = usePathname()
    const [time, setTime] = useState(null)
    const [tzIndex, setTzIndex] = useState(0)

    useEffect(() => {
        const savedTz = localStorage.getItem('phobert_timezone_idx')
        if (savedTz !== null) {
            setTzIndex(parseInt(savedTz, 10))
        }

        const tick = () => setTime(new Date())
        tick()
        const timerId = setInterval(tick, 1000)
        return () => clearInterval(timerId)
    }, [])

    const handleTzClick = () => {
        const nextIdx = (tzIndex + 1) % TIMEZONES.length
        setTzIndex(nextIdx)
        localStorage.setItem('phobert_timezone_idx', nextIdx.toString())
    }

    const formatTime = (date, timezone) => {
        if (!date) return { time: '--:--:--', date: '--/--/----' }
        const timeStr = date.toLocaleTimeString('vi-VN', {
            timeZone: timezone.zone,
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        })
        const dateStr = date.toLocaleDateString('vi-VN', {
            timeZone: timezone.zone,
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        })
        return { time: timeStr, date: dateStr }
    }

    const timeData = time ? formatTime(time, TIMEZONES[tzIndex]) : { time: '--:--:--', date: '--/--/----' }

    return (
        <nav className={styles.navbar}>
            <div className={styles.inner}>
                <Link href="/" className={styles.brand}>
                    <div className={styles.brandIcon}>⚡</div>
                    <span className={styles.brandName}>CyberAI Assessment</span>
                </Link>

                <div className={styles.nav}>
                    {NAV_ITEMS.map(item => (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`${styles.link} ${pathname === item.href ? styles.linkActive : ''}`}
                        >
                            <span>{item.icon}</span>
                            <span>{item.label}</span>
                        </Link>
                    ))}
                </div>

                <div className={styles.rightSection}>
                    <div className={styles.status}>
                        <span className={styles.dot} />
                        <span>Online</span>
                    </div>
                    <div className={styles.clock} onClick={handleTzClick} title="Nhấn để đổi Múi giờ">
                        <span className={styles.clockIcon}>🕒</span>
                        <div className={styles.timeWrapper} suppressHydrationWarning>
                            <span className={styles.timeText}>{timeData.time}</span>
                            <span className={styles.dateText}>{timeData.date}</span>
                        </div>
                        <span className={styles.tzLabel}>{TIMEZONES[tzIndex].label}</span>
                    </div>
                </div>
            </div>
        </nav>
    )
}
