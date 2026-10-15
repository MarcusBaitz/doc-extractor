import { defineConfig } from 'vitest/config'

// Keep this separate from vite.config.ts: Vitest 4 no longer augments the Vite
// configuration type, and a cast would only hide the next type error.
export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/frontend/**/*.test.{ts,tsx}'],
  },
})
