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
		margin: 0;
		padding: 0;
		overflow: hidden;
		background: black;
		color: white;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
	}

	.start-overlay {
		width: 100vw;
		height: 100vh;
		background: #0f0f23;
		border: none;
		cursor: pointer;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
	}

	.start-title {
		font-size: 5rem;
		font-weight: 700;
		margin: 0;
		color: white;
		letter-spacing: 0.05em;
	}

	.start-hint {
		font-size: 1.3rem;
		margin: 0;
		color: #aaa;
	}

	.display {
		width: 100vw;
		height: 100vh;
		position: relative;
	}
</style>
