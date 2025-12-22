import { defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';

const normalizeBaseForVite = (value) => {
	if (!value || value === '/') {
		return '/';
	}
	const base = value.replace(/^\/+|\/+$/g, '');
	return `/${base}/`;
};

// https://vitejs.dev/config/
export default defineConfig({
	base: normalizeBaseForVite(process.env.VITE_BASE_PATH),
	plugins: [
		sveltekit(),
	],
	server: {
		port: 8080
	}
})
