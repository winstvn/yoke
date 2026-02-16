<script lang="ts">
	import QRCodeStyling from 'qr-code-styling';
	import { resolveControlUrl } from '$lib/control-url';

	let controlUrl = $state('');
	let qrContainer: HTMLDivElement;

	$effect(() => {
		resolveControlUrl().then((url) => {
			controlUrl = url;
			const qr = new QRCodeStyling({
				width: 200,
				height: 200,
				type: 'svg',
				data: url,
				dotsOptions: {
					color: '#ffffff',
					type: 'rounded'
				},
				cornersSquareOptions: {
					type: 'extra-rounded'
				},
				cornersDotOptions: {
					type: 'dot'
				},
				backgroundOptions: {
					color: 'transparent'
				}
			});
			qrContainer.innerHTML = '';
			qr.append(qrContainer);
		});
	});
</script>

<div class="idle-screen">
	<h1 class="title">Yoke</h1>
	<p class="subtitle">Scan to join or visit:</p>
	<div class="qr-wrapper" bind:this={qrContainer}></div>
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="url-box" onclick={(e) => e.stopPropagation()}>{controlUrl}</div>
	<p class="tip">Click anywhere to toggle fullscreen</p>
</div>

<style>
	.idle-screen {
		width: 100vw;
		height: 100vh;
		background: var(--bg-deep);
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		position: relative;
	}

	.idle-screen::after {
		content: '';
		position: absolute;
		inset: 0;
		pointer-events: none;
		background: repeating-linear-gradient(
			0deg,
			transparent,
			transparent 2px,
			rgba(0, 0, 0, 0.06) 2px,
			rgba(0, 0, 0, 0.06) 4px
		);
		animation: scanline-scroll 0.3s linear infinite;
	}

	.title {
		font-size: 5rem;
		font-weight: 700;
		margin: 0;
		color: var(--amber);
		letter-spacing: 0.1em;
		text-shadow:
			0 0 10px var(--amber-glow),
			0 0 30px var(--amber-glow),
			0 0 60px rgba(255, 157, 0, 0.2);
		animation: flicker 4s infinite;
	}

	.subtitle {
		font-size: 1.3rem;
		margin: 0;
		color: var(--text-secondary);
	}

	.qr-wrapper {
		display: flex;
		align-items: center;
		justify-content: center;
		filter: drop-shadow(0 0 8px var(--amber-glow));
	}

	.url-box {
		font-family: var(--font-mono);
		font-size: 1.2rem;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		padding: 0.75rem 1.5rem;
		border-radius: 4px;
		color: var(--amber);
		word-break: break-all;
		text-align: center;
	}

	.tip {
		font-size: 0.9rem;
		margin: 0;
		color: var(--text-dim);
	}
</style>
