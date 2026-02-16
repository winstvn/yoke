<script lang="ts">
	import { get } from 'svelte/store';
	import VideoPlayer from '$lib/components/VideoPlayer.svelte';
	import Notifications from '$lib/components/Notifications.svelte';
	import FloatingMessages from '$lib/components/FloatingMessages.svelte';
	import QrOverlay from '$lib/components/QrOverlay.svelte';
	import IdleScreen from '$lib/components/IdleScreen.svelte';
	import { getSocket, initSession, currentItem } from '$lib/stores/session';

	let started = $state(false);
	let current = $state(get(currentItem));

	$effect(() => {
		const unsub = currentItem.subscribe((val) => {
			current = val;
		});
		return unsub;
	});

	function start() {
		started = true;
		const socket = getSocket();
		socket.connect();
		initSession(socket);
	}

	function toggleFullscreen() {
		if (document.fullscreenElement) {
			document.exitFullscreen();
		} else {
			document.documentElement.requestFullscreen();
		}
	}
</script>

<svelte:head>
	<title>Yoke — Display</title>
</svelte:head>

{#if !started}
	<button class="start-overlay" onclick={start}>
		<h1 class="start-title">Yoke</h1>
		<p class="start-hint">Click anywhere to start</p>
	</button>
{:else}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="display" onclick={toggleFullscreen}>
		{#if current}
			<VideoPlayer />
		{:else}
			<IdleScreen />
		{/if}
		<Notifications />
		<FloatingMessages />
		<QrOverlay />
	</div>
{/if}

<style>
	:global(body) {
		overflow: hidden;
	}

	.start-overlay {
		width: 100vw;
		height: 100vh;
		background: var(--bg-deep);
		border: none;
		cursor: pointer;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		font-family: var(--font-mono);
	}

	.start-title {
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

	.start-hint {
		font-size: 1.3rem;
		margin: 0;
		color: var(--text-secondary);
	}

	.display {
		width: 100vw;
		height: 100vh;
		position: relative;
	}
</style>
