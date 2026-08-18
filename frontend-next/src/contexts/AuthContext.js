'use client'

import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const AuthContext = createContext({
    user: null,
    token: null,
    isAuthenticated: false,
    loading: true,
    login: async () => {},
    register: async () => {},
    logout: () => {},
})

const TOKEN_KEY = 'cyberai_auth_token'
const USER_KEY = 'cyberai_auth_user'

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null)
    const [token, setToken] = useState(null)
    const [loading, setLoading] = useState(true)

    // Load persisted token and user on mount
    useEffect(() => {
        try {
            const savedToken = localStorage.getItem(TOKEN_KEY)
            const savedUser = localStorage.getItem(USER_KEY)
            if (savedToken && savedUser) {
                setToken(savedToken)
                setUser(JSON.parse(savedUser))
                // Verify with backend
                fetch('/api/auth/me', {
                    headers: { Authorization: `Bearer ${savedToken}` }
                })
                .then(res => res.ok ? res.json() : null)
                .then(verifiedUser => {
                    if (verifiedUser) {
                        setUser(verifiedUser)
                        localStorage.setItem(USER_KEY, JSON.stringify(verifiedUser))
                    } else {
                        // Token expired or invalid
                        localStorage.removeItem(TOKEN_KEY)
                        localStorage.removeItem(USER_KEY)
                        setToken(null)
                        setUser(null)
                    }
                })
                .catch(() => {})
            }
        } catch {}
        finally {
            setLoading(false)
        }
    }, [])

    const login = useCallback(async (username, password) => {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        })
        const text = await res.text()
        let data = {}
        try {
            data = JSON.parse(text)
        } catch (_) {
            data = { detail: text || 'Lỗi phản hồi từ máy chủ' }
        }
        if (!res.ok) {
            throw new Error(data.detail || data.error || 'Đăng nhập thất bại')
        }
        setToken(data.token)
        setUser(data.user)
        try {
            localStorage.setItem(TOKEN_KEY, data.token)
            localStorage.setItem(USER_KEY, JSON.stringify(data.user))
        } catch {}
        return data.user
    }, [])

    const register = useCallback(async ({ username, password, email, full_name, role }) => {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, email, full_name, role })
        })
        const text = await res.text()
        let data = {}
        try {
            data = JSON.parse(text)
        } catch (_) {
            data = { detail: text || 'Lỗi phản hồi từ máy chủ' }
        }
        if (!res.ok) {
            throw new Error(data.detail || data.error || 'Đăng ký thất bại')
        }
        setToken(data.token)
        setUser(data.user)
        try {
            localStorage.setItem(TOKEN_KEY, data.token)
            localStorage.setItem(USER_KEY, JSON.stringify(data.user))
        } catch {}
        return data.user
    }, [])

    const logout = useCallback(() => {
        try {
            fetch('/api/auth/logout', { method: 'POST' }).catch(() => {})
            localStorage.removeItem(TOKEN_KEY)
            localStorage.removeItem(USER_KEY)
        } catch {}
        setToken(null)
        setUser(null)
    }, [])

    return (
        <AuthContext.Provider value={{
            user,
            token,
            isAuthenticated: !!user,
            loading,
            login,
            register,
            logout
        }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    return useContext(AuthContext)
}
