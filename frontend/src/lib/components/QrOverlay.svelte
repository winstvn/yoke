<script lang="ts">
	import { showQr } from '$lib/stores/session';
	import { get } from 'svelte/store';

	let visible = $state(get(showQr));

	$effect(() => {
		const unsub = showQr.subscribe((val) => {
			visible = val;
		});
		return unsub;
	});

	let controlUrl = $state('');

	$effect(() => {
		if (typeof window !== 'undefined') {
			const { protocol, hostname, port } = window.location;
			const portPart = port ? `:${port}` : '';
			controlUrl = `${protocol}//${hostname}${portPart}/control`;
		}
	});
</script>

{#if visible}
	<div class="qr-overlay">
		<div class="qr-card">
			<p class="qr-label">Join the session!</p>
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
		background: white;
		color: #1a1a2e;
		padding: 1.25rem 1.5rem;
		border-radius: 12px;
		box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
		text-align: center;
		max-width: 320px;
	}

	.qr-label {
		margin: 0 0 0.5rem;
		font-size: 1.1rem;
		font-weight: 600;
	}

	.qr-url {
		margin: 0;
		font-size: 0.95rem;
		font-family: 'SF Mono', 'Fira Code', monospace;
		background: #f0f0f5;
		padding: 0.5rem 0.75rem;
		border-radius: 6px;
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
