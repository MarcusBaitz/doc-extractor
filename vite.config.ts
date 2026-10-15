import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Tauri serves the production frontend from the bundle. In development, the
// Vite server uses the fixed port recorded in tauri.conf.json.
export default defineConfig({
  plugins: [react(), tailwindcss()],

  // Tauri records this address in configuration, so a changing port would
  // break development startup.
  server: {
    port: 5183,
    strictPort: true,
    watch: {
      // Rust and Python sources do not trigger frontend reloads.
      ignored: ['**/src-tauri/**', '**/sidecar/**', '**/corpus/out/**'],
    },
  },

  // The application runs only in the Tauri webview, so it targets a modern
  // environment without legacy-browser support.
  build: {
    target: 'es2022',
    sourcemap: true,
    outDir: 'dist',
  },
})
