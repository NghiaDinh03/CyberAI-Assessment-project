/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
    async rewrites() {
        return [
            {
                source: '/api/docs/:path*',
                destination: '/api/docs/:path*'
            },
            {
                source: '/api/:path*',
                destination: `${process.env.API_URL || 'http://backend:8000'}/api/:path*`
            }
        ]
    }
}

export default nextConfig
