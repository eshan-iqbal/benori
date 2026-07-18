
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://3.222.251.93:8000/:path*',
      },
    ]
  },
};

export default nextConfig;
