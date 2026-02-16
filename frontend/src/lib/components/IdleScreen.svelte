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
	<div class="url-box">{controlUrl}</div>
</div>

<style>
	.idle-screen {
		width: 100vw;
		height: 100vh;
		background: #0f0f23;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
	}

	.title {
		font-size: 5rem;
		font-weight: 700;
		margin: 0;
		color: white;
		letter-spacing: 0.05em;
	}

	.subtitle {
		font-size: 1.3rem;
		margin: 0;
		color: #aaa;
	}

	.qr-wrapper {
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.url-box {
		font-family: 'SF Mono', 'Fira Code', 'Courier New', monospace;
		font-size: 1.2rem;
		background: rgba(255, 255, 255, 0.08);
		border: 1px solid rgba(255, 255, 255, 0.15);
		padding: 0.75rem 1.5rem;
		border-radius: 8px;
		color: white;
		word-break: break-all;
		text-align: center;
	}
</style>
