'use client'

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { Shield, Loader2 } from 'lucide-react'

export default function AuthGuard({ children }) {
    const { isAuthenticated, loading } = useAuth()
    const router = useRouter()
    const pathname = usePathname()

    const isPublicPage = pathname === '/login'

    useEffect(() => {
        if (!loading && !isAuthenticated && !isPublicPage) {
            router.replace('/login')
        }
    }, [isAuthenticated, loading, isPublicPage, router])

    if (loading && !isPublicPage) {
        return (
            <div style={{
                minHeight: '100vh',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '12px',
                background: 'var(--bg-primary, #0a0f1d)',
                color: 'var(--text-primary, #f1f5f9)'
            }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '48px',
                    height: '48px',
                    borderRadius: '12px',
                    background: 'rgba(37, 99, 235, 0.15)',
                    border: '1px solid rgba(37, 99, 235, 0.3)',
                    color: '#60a5fa'
                }}>
                    <Shield size={24} />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.86rem', color: '#94a3b8' }}>
                    <Loader2 size={16} className="spin-icon" style={{ animation: 'spin 1s linear infinite' }} />
                    <span>Đang kiểm tra xác thực tài khoản...</span>
                </div>
                <style jsx global>{`
                    @keyframes spin {
                        from { transform: rotate(0deg); }
                        to { transform: rotate(360deg); }
                    }
                `}</style>
            </div>
        )
    }

    if (!isAuthenticated && !isPublicPage) {
        return null
    }

    return children
}
