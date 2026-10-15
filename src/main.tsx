import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './App'
import { applyTheme, storedTheme } from './design/theme'
import './index.css'

// Apply the stored theme before the first paint to avoid a meaningless flash.
applyTheme(storedTheme())

const root = document.getElementById('root')
if (!root) throw new Error('Root element #root is missing from index.html')

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
