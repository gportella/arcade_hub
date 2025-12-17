export const manifest = (() => {
function __memo(fn) {
	let value;
	return () => value ??= (value = fn());
}

return {
	appDir: "_app",
	appPath: "_app",
	assets: new Set(["assets/bg.png","assets/logo.png","assets/star.png","favicon.png"]),
	mimeTypes: {".png":"image/png"},
	_: {
		client: {start:"_app/immutable/entry/start.4bTOcig6.js",app:"_app/immutable/entry/app.DGxXEXX1.js",imports:["_app/immutable/entry/start.4bTOcig6.js","_app/immutable/chunks/DvGf2eo5.js","_app/immutable/chunks/DRrBpfaE.js","_app/immutable/chunks/BndLyWgi.js","_app/immutable/entry/app.DGxXEXX1.js","_app/immutable/chunks/DRrBpfaE.js","_app/immutable/chunks/DBHc2DkE.js","_app/immutable/chunks/bbbXW2FV.js","_app/immutable/chunks/Cy6Kf354.js","_app/immutable/chunks/BndLyWgi.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./nodes/0.js')),
			__memo(() => import('./nodes/1.js')),
			__memo(() => import('./nodes/2.js'))
		],
		routes: [
			{
				id: "/",
				pattern: /^\/$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 2 },
				endpoint: null
			}
		],
		prerendered_routes: new Set([]),
		matchers: async () => {
			
			return {  };
		},
		server_assets: {}
	}
}
})();
