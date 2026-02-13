<script lang="ts">
	import { notifications } from '$lib/stores/session';
	import { get } from 'svelte/store';

	let items = $state(get(notifications));

	$effect(() => {
		const unsub = notifications.subscribe((val) => {
			items = val;
		});
		return unsub;
	});
</script>

<div class="notifications">
	{#each items as notif (notif.id)}
		<div class="notification">
			{notif.text}
		</div>
	{/each}
</div>

<style>
	.notifications {
		position: fixed;
		top: 1.5rem;
		right: 0;
		z-index: 100;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		pointer-events: none;
	}

	.notification {
		background: rgba(20, 20, 40, 0.85);
		color: white;
		padding: 0.75rem 1.25rem;
		font-size: 1.2rem;
		border-radius: 8px 0 0 8px;
		animation: slideIn 0.3s ease-out forwards, slideOut 0.4s ease-in 3.5s forwards;
		pointer-events: auto;
		max-width: 400px;
		word-break: break-word;
	}

	@keyframes slideIn {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	@keyframes slideOut {
		from {
			transform: translateX(0);
			opacity: 1;
		}
		to {
			transform: translateX(100%);
			opacity: 0;
		}
	}
</style>
