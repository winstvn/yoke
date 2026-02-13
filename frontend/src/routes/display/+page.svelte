<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import VideoPlayer from '$lib/components/VideoPlayer.svelte';
	import Notifications from '$lib/components/Notifications.svelte';
	import FloatingMessages from '$lib/components/FloatingMessages.svelte';
	import QrOverlay from '$lib/components/QrOverlay.svelte';
	import IdleScreen from '$lib/components/IdleScreen.svelte';
	import { getSocket, initSession, currentItem } from '$lib/stores/session';

	let current = $state(get(currentItem));

	$effect(() => {
		const unsub = currentItem.subscribe((val) => {
			current = val;
		});
		return unsub;
	});

	onMount(() => {
		const socket = getSocket();
		socket.connect();
		initSession(socket);
		return () => socket.disconnect();
	});
</script>

<svelte:head>
	<title>Yoke — Display</title>
</svelte:head>

<div class="display">
	{#if current}
		<VideoPlayer />
	{:else}
		<IdleScreen />
	{/if}
	<Notifications />
	<FloatingMessages />
	<QrOverlay />
</div>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		overflow: hidden;
		background: black;
		color: white;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
	}

	.display {
		width: 100vw;
		height: 100vh;
		position: relative;
	}
</style>
