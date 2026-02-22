<script lang="ts">
	import { getSocket } from '$lib/stores/session';
	import type { ConnectionState } from '$lib/ws';

	let {
		singerName,
		activeTab,
		isHost,
		onTabChange,
		connectionState = 'disconnected'
	}: {
		singerName: string;
		activeTab: string;
		isHost: boolean;
		onTabChange: (tab: string) => void;
		connectionState?: ConnectionState;
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
			<span class="singer-name">
				<span
					class="status-dot"
					class:connected={connectionState === 'connected'}
					class:connecting={connectionState === 'connecting'}
					class:disconnected={connectionState === 'disconnected'}
				></span>
				{singerName}
			</span>
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
		background: var(--bg-surface);
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
		color: var(--amber);
		text-shadow: 0 0 8px var(--amber-glow);
	}

	.header-right {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.singer-name {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		color: var(--text-secondary);
		font-size: 0.9rem;
	}

	.status-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.status-dot.connected {
		background-color: #4ade80;
		box-shadow: 0 0 4px #4ade80;
	}

	.status-dot.connecting {
		background-color: #facc15;
		box-shadow: 0 0 4px #facc15;
	}

	.status-dot.disconnected {
		background-color: #f87171;
		box-shadow: 0 0 4px #f87171;
	}

	.qr-button {
		padding: 0.4rem 0.75rem;
		border-radius: 4px;
		border: 1px solid var(--border);
		background: transparent;
		color: var(--amber);
		font-size: 0.85rem;
		font-family: var(--font-mono);
		cursor: pointer;
	}

	.qr-button:hover {
		border-color: var(--amber);
		box-shadow: 0 0 8px var(--amber-glow);
	}

	.tab-row {
		display: flex;
		border-bottom: 1px solid var(--border);
	}

	.tab {
		flex: 1;
		padding: 0.6rem 0;
		border: none;
		border-bottom: 2px solid transparent;
		background: transparent;
		color: var(--text-dim);
		font-size: 0.95rem;
		font-family: var(--font-mono);
		cursor: pointer;
		transition: color 0.15s, border-color 0.15s;
	}

	.tab:hover {
		color: var(--text-secondary);
	}

	.tab.active {
		color: var(--amber);
		border-bottom-color: var(--amber);
		text-shadow: 0 0 6px var(--amber-glow);
	}
</style>
