<script lang="ts">
	import { getSocket } from '$lib/stores/session';

	let {
		singerName,
		activeTab,
		isHost,
		onTabChange
	}: {
		singerName: string;
		activeTab: string;
		isHost: boolean;
		onTabChange: (tab: string) => void;
	} = $props();

	const tabs = $derived(
		isHost
			? ['Search', 'Queue', 'Settings']
			: ['Search', 'Queue']
	);

	function handleQr() {
		getSocket().send({ type: 'show_qr' });
	}
</script>

<div class="topbar">
	<div class="header-row">
		<span class="app-name">Yoke</span>
		<div class="header-right">
			<span class="singer-name">{singerName}</span>
			<button class="qr-button" onclick={handleQr} title="Show QR code">QR</button>
		</div>
	</div>
	<div class="tab-row">
		{#each tabs as tab}
			<button
				class="tab"
				class:active={activeTab === tab}
				onclick={() => onTabChange(tab)}
			>
				{tab}
			</button>
		{/each}
	</div>
</div>

<style>
	.topbar {
		position: sticky;
		top: 0;
		z-index: 100;
		background: #1a1a2e;
	}

	.header-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 1rem;
	}

	.app-name {
		font-size: 1.25rem;
		font-weight: 700;
		color: white;
	}

	.header-right {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.singer-name {
		color: #888;
		font-size: 0.9rem;
	}

	.qr-button {
		padding: 0.4rem 0.75rem;
		border-radius: 6px;
		border: 1px solid #444;
		background: transparent;
		color: white;
		font-size: 0.85rem;
		cursor: pointer;
	}

	.qr-button:hover {
		background: #2a2a4e;
	}

	.tab-row {
		display: flex;
		border-bottom: 1px solid #333;
	}

	.tab {
		flex: 1;
		padding: 0.6rem 0;
		border: none;
		border-bottom: 2px solid transparent;
		background: transparent;
		color: #888;
		font-size: 0.95rem;
		cursor: pointer;
		transition: color 0.15s, border-color 0.15s;
	}

	.tab:hover {
		color: #ccc;
	}

	.tab.active {
		color: white;
		border-bottom-color: #5555ff;
	}
</style>
