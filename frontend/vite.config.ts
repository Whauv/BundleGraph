import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

function authoritativeRuntimeConfig(): Plugin {
  return {
    name: 'bundlegraph-authoritative-runtime-config',
    configureServer(server) {
      if (process.env.VITE_BUNDLEGRAPH_RUNTIME !== 'authoritative') return;
      server.middlewares.use('/runtime-config', (request, response, next) => {
        if (request.method !== 'GET') { next(); return; }
        response.statusCode = 200;
        response.setHeader('Content-Type', 'application/json');
        response.end(JSON.stringify({
          runtime: 'application',
          api_base: process.env.VITE_BUNDLEGRAPH_API_BASE || '',
          authentication: null,
          capabilities: { planning: true, candidate_discovery: true, live_candidate_provider: false, payments: false },
        }));
      });
    },
  };
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), authoritativeRuntimeConfig()],
})
