import { defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: 5173,
		strictPort: true,
		host: true,
		allowedHosts: [
			'families.loginto.me',
			'familyherohub.com',
			'www.familyherohub.com',
			'localhost',
			'127.0.0.1'
		],
		proxy: {
			'/api': {
				target: 'http://backend:8000',
				changeOrigin: true
			}
		}
	}
});
