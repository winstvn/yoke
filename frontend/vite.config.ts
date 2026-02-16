import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
const backendWs = backendUrl.replace(/^http/, 'ws');

export default defineConfig({
	plugins: [sveltekit()],
	ssr: {
		noExternal: ['qr-code-styling']
	},
	server: {
		host: true,
		proxy: {
			'/api': backendUrl,
			'/ws': {
				target: backendWs,
				ws: true
			},
			'/videos': backendUrl
		}
	}
});
