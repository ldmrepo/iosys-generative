import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Enable standalone output for Docker deployment
  output: 'standalone',

  // Transpile workspace packages
  transpilePackages: ['@iosys/qti-core', '@iosys/qti-ui', '@iosys/qti-viewer'],

  // API rewrites to backend
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ]
  },
}

export default nextConfig
