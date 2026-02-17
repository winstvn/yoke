<script lang="ts">
	import { onMount } from 'svelte';
	import { get } from 'svelte/store';
	import NameEntry from '$lib/components/NameEntry.svelte';
	import TopBar from '$lib/components/TopBar.svelte';
	import PlaybackBar from '$lib/components/PlaybackBar.svelte';
	import SearchTab from '$lib/components/SearchTab.svelte';
	import QueueTab from '$lib/components/QueueTab.svelte';
	import SettingsTab from '$lib/components/SettingsTab.svelte';
	import MessageInput from '$lib/components/MessageInput.svelte';
	import { getSocket, initSession, settings } from '$lib/stores/session';


	const STORAGE_KEY = 'yoke_singer_name';
	const STORAGE_ID_KEY = 'yoke_singer_id';
	const TAB_KEY = 'yoke_active_tab';
	const VALID_TABS = ['Search', 'Queue', 'Settings'];

	let joined = $state(false);
	let singerName = $state('');
	let singerId = $state('');
	let activeTab = $state(restoreTab());

	function restoreTab(): string {
		if (typeof sessionStorage === 'undefined') return 'Search';
		const saved = sessionStorage.getItem(TAB_KEY);
		return saved && VALID_TABS.includes(saved) ? saved : 'Search';
	}

	let settingsValue = $state(get(settings));

	$effect(() => {
		const unsubSettings = settings.subscribe((val) => {
			settingsValue = val;
		});
		return () => {
			unsubSettings();
		};
	});

	let isHost = $derived(singerId !== '' && settingsValue.host_id === singerId);

	function handleJoin(name: string) {
		singerName = name;
		localStorage.setItem(STORAGE_KEY, name);

		const socket = getSocket();
		socket.connect();
		initSession(socket);

		// Listen for state message to get our singer ID
		socket.onMessage((msg) => {
			if (msg.type === 'state' && msg.singer_id) {
				singerId = msg.singer_id;
				localStorage.setItem(STORAGE_ID_KEY, msg.singer_id);
			}
		});

		const savedId = localStorage.getItem(STORAGE_ID_KEY) ?? undefined;
		socket.send({ type: 'join', name, singer_id: savedId });
		joined = true;
	}

	function handleTabChange(tab: string) {
		activeTab = tab;
		sessionStorage.setItem(TAB_KEY, tab);
	}

	onMount(() => {
		const savedName = localStorage.getItem(STORAGE_KEY);
		if (savedName) {
			handleJoin(savedName);
		}
	});
</script>

<svelte:head>
	<title>Yoke</title>
</svelte:head>

{#if !joined}
	<NameEntry onJoin={handleJoin} />
{:else}
	<TopBar {singerName} {activeTab} {isHost} onTabChange={handleTabChange} />

	<main class="content">
		{#if activeTab === 'Search'}
			<SearchTab />
		{:else if activeTab === 'Queue'}
			<QueueTab {singerId} {isHost} />
		{:else if activeTab === 'Settings'}
			<SettingsTab />
		{/if}
	</main>

	<div class="bottom-bar">
		<MessageInput />
		<PlaybackBar />
	</div>
{/if}

<style>
	.content {
		padding: 1rem;
		padding-bottom: 14rem;
	}

	.bottom-bar {
		position: fixed;
		bottom: 0;
		left: 0;
		right: 0;
		z-index: 100;
		display: flex;
		flex-direction: column;
	}
</style>
