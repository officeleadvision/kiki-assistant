import typography from '@tailwindcss/typography';
import containerQueries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				primary: {
					DEFAULT: '#1e3a5f',
					50: '#f0f5fa',
					100: '#dae6f2',
					200: '#b8cfe6',
					300: '#8bb3d5',
					400: '#5a93c2',
					500: '#3a78ad',
					600: '#2d5f8f',
					700: '#264d74',
					800: '#1e3a5f',
					900: '#172d4a',
					950: '#0f1f33'
				},
				gray: {
					50: 'var(--color-gray-50, #ffffff)',
					100: 'var(--color-gray-100, #f8fafc)',
					200: 'var(--color-gray-200, #f1f5f9)',
					300: 'var(--color-gray-500, #e2e8f0)',
					400: 'var(--color-gray-400, #cbd5e1)',
					500: 'var(--color-gray-500, #94a3b8)',
					600: 'var(--color-gray-600, #64748b)',
					700: 'var(--color-gray-700, #475569)',
					800: 'var(--color-gray-800, #334155)',
					850: 'var(--color-gray-850, #1e293b)',
					900: 'var(--color-gray-900, #0f172a)',
					950: 'var(--color-gray-950, #020617)'
				}
			},
			typography: {
				DEFAULT: {
					css: {
						pre: false,
						code: false,
						'pre code': false,
						'code::before': false,
						'code::after': false
					}
				}
			},
			padding: {
				'safe-bottom': 'env(safe-area-inset-bottom)'
			},
			transitionProperty: {
				width: 'width'
			}
		}
	},
	plugins: [typography, containerQueries]
};
