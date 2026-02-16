<script lang="ts">
	import QRCodeStyling from 'qr-code-styling';
	import { showQr } from '$lib/stores/session';
	import { resolveControlUrl } from '$lib/control-url';
	import { get } from 'svelte/store';

	let visible = $state(get(showQr));

	$effect(() => {
		const unsub = showQr.subscribe((val) => {
			visible = val;
		});
		return unsub;
	});

	let controlUrl = $state('');
	let qrContainer = $state<HTMLDivElement | null>(null);

	$effect(() => {
		resolveControlUrl().then((url) => {
			controlUrl = url;
		});
	});

	$effect(() => {
		if (!controlUrl || !qrContainer) return;
		const qr = new QRCodeStyling({
			width: 160,
			height: 160,
			type: 'svg',
			data: controlUrl,
			dotsOptions: {
				color: '#ff9d00',
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
</script>

{#if visible}
	<div class="qr-overlay">
		<div class="qr-card">
			<p class="qr-label">Join the session!</p>
			<div class="qr-wrapper" bind:this={qrContainer}></div>
			<p class="qr-url">{controlUrl}</p>
		</div>
	</div>
{/if}

<style>
	.qr-overlay {
		position: fixed;
		bottom: 2rem;
		right: 2rem;
		z-index: 95;
		animation: fadeIn 0.3s ease-out forwards;
	}

	.qr-card {
		background: var(--bg-surface);
		color: var(--text-primary);
		padding: 1.25rem 1.5rem;
		border-radius: 4px;
		border: 1px solid var(--amber);
		box-shadow: 0 0 20px var(--amber-glow);
		text-align: center;
		max-width: 320px;
	}

	.qr-label {
		margin: 0 0 0.75rem;
		font-size: 1.1rem;
		font-weight: 600;
		color: var(--amber-bright);
	}

	.qr-wrapper {
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 0.5rem;
	}

	.qr-url {
		margin: 0;
		font-size: 0.85rem;
		font-family: var(--font-mono);
		background: var(--bg-deep);
		color: var(--amber);
		padding: 0.5rem 0.75rem;
		border-radius: 4px;
		word-break: break-all;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
