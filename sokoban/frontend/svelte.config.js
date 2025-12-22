import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

const rawBasePath = process.env.VITE_BASE_PATH ?? '';
const basePath = (() => {
	const trimmed = rawBasePath.trim();
	if (!trimmed || trimmed === '/') {
		return '';
	}
	const withoutSlashes = trimmed.replace(/^\/+|\/+$/g, '');
	return `/${withoutSlashes}`;
})();
const assetsPath = basePath ? `.${basePath}` : '';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://kit.svelte.dev/docs/integrations#preprocessors
	// for more information about preprocessors
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter({
			precompress: false,
			fallback: 'index.html'
		}),
		paths: {
			base: basePath,
			assets: assetsPath,
		},
	}
};

export default config;
