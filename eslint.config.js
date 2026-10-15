// @ts-check
import js from '@eslint/js'
import reactHooks from 'eslint-plugin-react-hooks'
import tseslint from 'typescript-eslint'

/**
 * The most important rule appears at the bottom: the frontend cannot access
 * the network. Outbound traffic passes only through the chokepoint in
 * `src-tauri/src/egress.rs`; backend calls use `src-tauri/src/bridge.rs`.
 *
 * This technically enforces the promise that nothing leaves the
 * infrastructure. Frontend `fetch` would bypass the audit log.
 */
export default tseslint.config(
  {
    ignores: ['dist/**', 'src-tauri/**', 'node_modules/**', 'corpus/out/**'],
  },

  js.configs.recommended,
  ...tseslint.configs.recommended,

  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
    },
    plugins: {
      'react-hooks': reactHooks,
    },
    rules: {
      // These two established rules catch hooks in conditions and stale state
      // caused by missing dependencies.
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',

      // The remaining `recommended` rules (set-state-in-effect, immutability,
      // and others) check React Compiler compatibility. This project does not
      // use that compiler, and those rules reject valid patterns such as
      // asynchronous loading followed by setState. Revisit on migration.
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      '@typescript-eslint/consistent-type-imports': [
        'error',
        { prefer: 'type-imports', fixStyle: 'inline-type-imports' },
      ],
    },
  },

  // --- Colour gate ---------------------------------------------------------
  //
  // The design language has exactly eight surface/text values and four
  // semantic colours, all in `src/design/tokens.css`. `bg-slate-800` in a
  // component would be an undeclared ninth surface that breaks one theme.
  //
  // `text-white` and `bg-white` remain allowed: white on a semantic colour is
  // contrast rather than a theme surface.
  {
    files: ['src/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-syntax': [
        'error',
        {
          selector:
            'Literal[value=/\\b(?:bg|text|border|ring|fill|stroke|divide|outline|decoration|placeholder|accent|caret|shadow|from|via|to)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\\d{2,3}\\b/]',
          message:
            'Do not use a default colour name. Colours live in src/design/tokens.css as bg-card, text-ink-2, border-line, text-good and bg-warn-bg; see docs/design/design-language.md.',
        },
        {
          selector:
            'TemplateElement[value.raw=/\\b(?:bg|text|border|ring|fill|stroke|divide|outline|decoration|placeholder|accent|caret|shadow|from|via|to)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\\d{2,3}\\b/]',
          message:
            'Do not use a default colour name. Colours live in src/design/tokens.css; see docs/design/design-language.md.',
        },
      ],
    },
  },

  // --- Egress gate ---------------------------------------------------------
  {
    files: ['src/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-globals': [
        'error',
        {
          name: 'fetch',
          message:
            'No frontend network access. Backend calls use src/api/client.ts (Tauri invoke); outbound traffic uses src-tauri/src/egress.rs.',
        },
        {
          name: 'XMLHttpRequest',
          message: 'No frontend network access; see src/api/client.ts.',
        },
        {
          name: 'WebSocket',
          message: 'No frontend network access; see src/api/client.ts.',
        },
        {
          name: 'EventSource',
          message: 'No frontend network access; see src/api/client.ts.',
        },
      ],
      'no-restricted-properties': [
        'error',
        {
          object: 'window',
          property: 'fetch',
          message: 'No frontend network access; see src/api/client.ts.',
        },
        {
          object: 'globalThis',
          property: 'fetch',
          message: 'No frontend network access; see src/api/client.ts.',
        },
        {
          object: 'navigator',
          property: 'sendBeacon',
          message: 'No telemetry; see docs/decisions.md.',
        },
      ],
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: 'axios',
              message: 'No HTTP client in the frontend; see src/api/client.ts.',
            },
            {
              name: '@tauri-apps/plugin-http',
              message:
                'Network access passes through the chokepoint in src-tauri/src/egress.rs, not the HTTP plugin.',
            },
          ],
        },
      ],
    },
  },
)
