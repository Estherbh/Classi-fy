module.exports = {
  root: true,
  env: {
    browser: true,
    es2020: true,
    node: true
  },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended'
  ],
  ignorePatterns: [
    'dist',
    '.eslintrc.js',
    'node_modules',
    'coverage',
    '*.config.js',
    'api/**/*'
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true
    }
  },
  settings: {
    react: {
      version: '18.2'
    }
  },
  plugins: [
    'react',
    'react-hooks'
  ],
  rules: {
    // Règles React simplifiées
    'react/prop-types': 'off', // Désactivé car on utilise TypeScript dans le futur
    'react/react-in-jsx-scope': 'off', // Pas nécessaire avec React 17+
    'react/jsx-uses-react': 'off', // Pas nécessaire avec React 17+
    'react/jsx-key': 'error',
    'react/jsx-no-duplicate-props': 'error',
    'react/jsx-no-undef': 'error',
    'react/jsx-uses-vars': 'error',
    'react/self-closing-comp': 'warn',
    
    // Règles React Hooks
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',
    
    // Règles générales JavaScript (simplifiées)
    'no-unused-vars': ['warn', { 
      argsIgnorePattern: '^_',
      varsIgnorePattern: '^_'
    }],
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'warn',
    'no-eval': 'error',
    'no-var': 'error',
    'prefer-const': 'error',
    
    // Désactiver les règles qui causent des problèmes de build
    'no-undef': 'off', // Peut causer des problèmes avec les globals
    'import/no-unresolved': 'off' // Désactivé car pas d'import plugin configuré
  },
  
  // Configuration spécifique pour les fichiers de test
  overrides: [
    {
      files: ['**/*.test.js', '**/*.test.jsx', '**/*.spec.js', '**/*.spec.jsx'],
      env: {
        jest: true
      },
      rules: {
        'no-console': 'off'
      }
    },
    {
      files: ['**/*.config.js', '**/vite.config.js', '**/tailwind.config.js', 'api/**/*.js'],
      rules: {
        'no-console': 'off'
      }
    }
  ]
}