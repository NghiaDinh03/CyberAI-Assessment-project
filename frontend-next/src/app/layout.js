import './globals.css'
import Navbar from '@/components/Navbar'
import ThemeProvider from '@/components/ThemeProvider'
import { ToastProvider } from '@/components/Toast'

export const metadata = {
    title: 'CyberAI Assessment Platform - Enterprise Edition',
    description: 'Nền tảng AI tiên tiến cho đánh giá tuân thủ ISO 27001:2022 & TCVN 14423',
    icons: { icon: '/favicon.ico' }
}

export default function RootLayout({ children }) {
    return (
        <html lang="vi">
            <body>
                <ThemeProvider>
                    <ToastProvider>
                        <Navbar />
                        <main>{children}</main>
                    </ToastProvider>
                </ThemeProvider>
            </body>
        </html>
    )
}
