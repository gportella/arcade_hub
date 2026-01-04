const BASE_URL = typeof import.meta !== "undefined" && import.meta.env ? import.meta.env.BASE_URL ?? "/" : "/";
const normalizedBase = BASE_URL.endsWith("/") && BASE_URL !== "/" ? BASE_URL.slice(0, -1) : BASE_URL === "/" ? "" : BASE_URL;

/**
 * Resolves a public asset path that respects the configured base URL.
 */
export const resolveAssetPath = (path) => {
  const sanitizedPath = path.startsWith("/") ? path.slice(1) : path;
  return `${normalizedBase}/${sanitizedPath}`;
};
