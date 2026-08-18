'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { useTranslation } from '@/components/LanguageProvider'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import styles from './login.module.css'

export default function LoginPage() {
    const router = useRouter()
    const { t } = useTranslation()
    const { login, isAuthenticated, loading: authLoading } = useAuth()
    
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    // Redirect to app if already authenticated
    useEffect(() => {
        if (!authLoading && isAuthenticated) {
            router.replace('/chatbot')
        }
    }, [isAuthenticated, authLoading, router])

    const handleSubmit = async (e) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            await login(username, password)
            router.push('/chatbot')
        } catch (err) {
            setError(err.message || 'Xảy ra lỗi trong quá trình xác thực.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className={styles.loginContainer}>
            {/* Ambient Background Grid */}
            <div className={styles.bgGrid} aria-hidden="true" />
            <div className={styles.bgGlow} aria-hidden="true" />

            <div className={styles.loginCard}>
                {/* Brand Header */}
                <div className={styles.brandHeader}>
                    <div className={styles.logoWrap}>
                        <svg className={styles.brandSvg} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M16 3L4 8v8c0 6.627 5.153 12.417 12 13.95C22.847 28.417 28 22.627 28 16V8L16 3z" fill="rgba(37,99,235,0.2)"/>
                            <path d="M16 3L4 8v8c0 6.627 5.153 12.417 12 13.95C22.847 28.417 28 22.627 28 16V8L16 3z" stroke="#3b82f6" strokeWidth="1.8" strokeLinejoin="round"/>
                            <path d="M11 16l3.5 3.5L21 12" stroke="#60a5fa" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                    </div>
                    <h1 className={styles.brandTitle}>{t('auth.brandTitle')}</h1>
                    <p className={styles.brandSubtitle}>
                        {t('auth.brandSubtitle')}
                    </p>
                </div>

                {/* Error Banner */}
                {error && (
                    <div className={styles.errorAlert} role="alert">
                        <span className={styles.errorDot} />
                        <span>{error}</span>
                    </div>
                )}

                {/* Auth Form */}
                <form onSubmit={handleSubmit} className={styles.authForm}>
                    <div className={styles.fieldGroup}>
                        <label className={styles.fieldLabel} htmlFor="username-input">
                            {t('auth.username')}
                        </label>
                        <input
                            id="username-input"
                            type="text"
                            className={styles.fieldInput}
                            placeholder={t('auth.usernamePlaceholder')}
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            required
                            autoFocus
                            autoComplete="username"
                        />
                    </div>

                    <div className={styles.fieldGroup}>
                        <div className={styles.labelRow}>
                            <label className={styles.fieldLabel} htmlFor="password-input">
                                {t('auth.password')}
                            </label>
                        </div>
                        <div className={styles.passwordWrapper}>
                            <input
                                id="password-input"
                                type={showPassword ? 'text' : 'password'}
                                className={styles.fieldInput}
                                placeholder={t('auth.passwordPlaceholder')}
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                required
                                autoComplete="current-password"
                            />
                            <button
                                type="button"
                                className={styles.togglePasswordBtn}
                                onClick={() => setShowPassword(!showPassword)}
                                aria-label="Toggle password visibility"
                            >
                                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                            </button>
                        </div>
                    </div>

                    <button
                        type="submit"
                        className={styles.primaryActionBtn}
                        disabled={loading || !username.trim() || !password.trim()}
                    >
                        {loading ? (
                            <span className={styles.loadingFlex}>
                                <Loader2 size={16} className={styles.spin} />
                                <span>{t('auth.authenticating')}</span>
                            </span>
                        ) : (
                            <span>{t('auth.submitLogin')}</span>
                        )}
                    </button>
                </form>

                {/* Enterprise Footer */}
                <div className={styles.cardFooter}>
                    <span>{t('auth.securityFooter')}</span>
                </div>
            </div>
        </div>
    )
}
