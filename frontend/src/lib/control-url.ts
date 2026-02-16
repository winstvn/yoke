/**
 * Resolves the control URL, substituting the server's LAN IP
 * when the page is accessed via localhost.
 */
export async function resolveControlUrl(): Promise<string> {
	const { protocol, hostname, port } = window.location;
	const portPart = port ? `:${port}` : '';

	let host = hostname;
	if (hostname === 'localhost' || hostname === '127.0.0.1') {
		try {
			const res = await fetch('/api/server-info');
			const info = await res.json();
			host = info.ip;
		} catch {
			// fall back to original hostname
		}
	}

	return `${protocol}//${host}${portPart}/control`;
}
