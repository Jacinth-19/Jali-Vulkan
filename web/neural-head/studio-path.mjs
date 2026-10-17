// Preserve canonical session bindings while routing a prepared-character studio.
// No origin/host rewriting: works with localhost and Arena's HTTPS preview proxy.
export function studioPath(path, pathname = globalThis.location?.pathname || '/') {
  if (typeof path !== 'string' || !path.startsWith('/') || path.startsWith('//')) return path;
  const match = /^\/characters\/(female|male)(?:\/|$)/.exec(pathname);
  return match ? `/characters/${match[1]}${path}` : path;
}
