'use client'

import { createContext, useContext, useState, useCallback, useRef } from 'react'
import styles from './Toast.module.css'

const ToastContext = createContext(null)

let _idCounter = 0
function nextId() { return ++_idCounter }

export function ToastProvider({ children }) {
    const [toasts, setToasts] = useState([])
    const timersRef = useRef({})

    const dismiss = useCallback((id) => {
        setToasts(prev => prev.filter(t => t.id !== id))
        if (timersRef.current[id]) {
            clearTimeout(timersRef.current[id])
            delete timersRef.current[id]
        }
    }, [])

    const showToast = useCallback((message, type = 'info') => {
        const id = nextId()
        setToasts(prev => {
            const next = [...prev, { id, message, type }]
            // Keep max 4 — drop oldest if exceeded
            return next.length > 4 ? next.slice(next.length - 4) : next
        })
        timersRef.current[id] = setTimeout(() => dismiss(id), 4000)
    }, [dismiss])

    return (
        <ToastContext.Provider value={{ showToast, toasts, dismiss }}>
            {children}
            <ToastContainer />
        </ToastContext.Provider>
    )
}

export function useToast() {
    const ctx = useContext(ToastContext)
    if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
    return ctx
}

const ICONS = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ',
}

function ToastContainer() {
    const ctx = useContext(ToastContext)
    if (!ctx) return null
    const { toasts, dismiss } = ctx

    return (
        <div className={styles.container} aria-live="polite" aria-label="Notifications">
            {toasts.map(t => (
                <div
                    key={t.id}
                    className={`${styles.toast} ${styles[t.type] || styles.info}`}
                    role="alert"
                >
                    <span className={styles.icon}>{ICONS[t.type] || ICONS.info}</span>
                    <span className={styles.message}>{t.message}</span>
                    <button
                        className={styles.close}
                        onClick={() => dismiss(t.id)}
                        aria-label="Dismiss notification"
                    >×</button>
                </div>
            ))}
        </div>
    )
}
