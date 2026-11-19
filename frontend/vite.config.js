import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'
import { ServerResponse } from 'node:http'
import process from 'node:process'


export default defineConfig(({ command, mode }) => {
  const frontendRoot = fileURLToPath(new URL('.', import.meta.url))
  // These values stay in the Vite server. Never expose the gateway token as VITE_*.
  const gatewayEnv = command === 'serve' ? {
    ...loadEnv(mode, fileURLToPath(new URL('../backend', import.meta.url)), 'QUANTNEST_'),
    ...loadEnv(mode, frontendRoot, 'QUANTNEST_'),
    ...process.env,
  } : {}
  const backendProxy = {
    target: gatewayEnv.QUANTNEST_API_PROXY_TARGET || 'http://127.0.0.1:8000',
    changeOrigin: false,
    ws: true,
    configure(proxy) {
      const prepareRequest = (upstream, request) => {
        for (const header of ['forwarded', 'x-forwarded-for', 'x-forwarded-host', 'x-forwarded-proto', 'x-quantnest-proxy-token', 'x-quantnest-client-ip']) {
          upstream.removeHeader(header)
        }
        if (gatewayEnv.QUANTNEST_PROXY_TOKEN) upstream.setHeader('X-QuantNest-Proxy-Token', gatewayEnv.QUANTNEST_PROXY_TOKEN)
        upstream.setHeader('X-Forwarded-Proto', request.socket.encrypted ? 'https' : 'http')
        upstream.setHeader('X-Forwarded-Host', request.headers.host)
        upstream.setHeader('X-Forwarded-For', request.socket.remoteAddress || '')
        upstream.setHeader('X-QuantNest-Client-IP', request.socket.remoteAddress || '')
      }
      proxy.on('proxyReq', prepareRequest)
      proxy.on('proxyReqWs', (upstream, request, socket) => {
        prepareRequest(upstream, request)
        // Vite's upgrade proxy forwards 101 responses but leaves HTTP rejections hanging.
        upstream.on('response', response => {
          const reply = new ServerResponse(request)
          reply.assignSocket(socket)
          reply.writeHead(response.statusCode ?? 502, { ...response.headers, connection: 'close' })
          response.pipe(reply)
        })
      })
    },
  }
  return {
    plugins: [react()],
    server: {
      proxy: Object.fromEntries(['/api/', '/ws/', '/admin', '/health', '/static/', '/media/'].map(path => [path, backendProxy])),
    },
    resolve: {
      alias: {
        "@": fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
  }
})
