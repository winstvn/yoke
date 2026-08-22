<script lang="ts">
	import { settings, getSocket } from '$lib/stores/session';
	import { TARGET_LUFS } from '$lib/audio/loudness';
	import { get } from 'svelte/store';

	let { isHost = false, canControlPlayback = false }: {
		isHost?: boolean;
		canControlPlayback?: boolean;
	} = $props();

	let settingsValue = $state(get(settings));
	let localVolume = $state(get(settings).volume);
	let dragging = $state(false);
	let sendTimer: ReturnType<typeof setTimeout> | null = null;

	$effect(() => {
		const unsub = settings.subscribe((val) => {
			settingsValue = val;
		});
		return () => {
			unsub();
		};
	});

	// Follow the server unless this singer is mid-drag, so a change made on
	// another phone shows up here without yanking the slider out from under them.
	$effect(() => {
		if (!dragging) localVolume = settingsValue.volume;
	});

	function sendVolume(value: number) {
		getSocket().send({ type: 'update_setting', key: 'volume', value });
	}

	function handleVolumeInput(e: Event) {
		dragging = true;
		localVolume = Number((e.currentTarget as HTMLInputElement).value) / 100;
		// Throttle while dragging; every send fans out to all clients.
		if (sendTimer) return;
		sendTimer = setTimeout(() => {
			sendTimer = null;
			sendVolume(localVolume);
		}, 100);
	}

	function handleVolumeCommit() {
		dragging = false;
		if (sendTimer) {
			clearTimeout(sendTimer);
			sendTimer = null;
		}
		sendVolume(localVolume);
	}

	function toggleReorder() {
		if (!isHost) return;
		getSocket().send({
			type: 'update_setting',
			key: 'anyone_can_reorder',
			value: !settingsValue.anyone_can_reorder
		});
	}
</script>

<div class="settings-tab">
	<h2 class="settings-heading">Settings</h2>

	<section class="setting-group">
		<h3 class="group-heading">Audio</h3>
		<div class="setting-card setting-card-static">
			<div class="volume-row">
				<span class="setting-label">Volume</span>
				<span class="volume-value">{Math.round(localVolume * 100)}%</span>
			</div>
			<input
				type="range"
				class="volume-slider"
				min="0"
				max="100"
				step="1"
				value={Math.round(localVolume * 100)}
				disabled={!canControlPlayback}
				oninput={handleVolumeInput}
				onchange={handleVolumeCommit}
				aria-label="Volume"
			/>
			<p class="setting-hint">
				{#if canControlPlayback}
					Songs are matched to {TARGET_LUFS} LUFS, so levels stay even between tracks.
				{:else}
					Only the current singer or the host can change the volume.
				{/if}
			</p>
		</div>
	</section>

	<section class="setting-group">
		<h3 class="group-heading">Queue</h3>
		<button
			class="setting-card"
			class:setting-card-disabled={!isHost}
			disabled={!isHost}
			onclick={toggleReorder}
		>
			<span class="setting-label">Allow everyone to reorder the queue</span>
			<span class="toggle" class:active={settingsValue.anyone_can_reorder}>
				<span class="toggle-knob"></span>
			</span>
		</button>
		{#if !isHost}
			<p class="setting-hint">Only the host can change this.</p>
		{/if}
	</section>
</div>

<style>
	.settings-tab {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.settings-heading {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--amber);
		margin: 0;
	}

	.setting-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.group-heading {
		font-size: 0.75rem;
		font-weight: 600;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-dim);
		margin: 0;
	}

	.setting-card {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 1rem;
		border-radius: 4px;
		border: 1px solid var(--border);
		background: var(--bg-surface);
		cursor: pointer;
		width: 100%;
		text-align: left;
		color: var(--text-primary);
		font-family: var(--font-mono);
	}

	.setting-card:hover:not(:disabled) {
		background: var(--bg-surface-hover);
	}

	.setting-card-disabled {
		cursor: not-allowed;
		opacity: 0.5;
	}

	.setting-card-static {
		display: flex;
		flex-direction: column;
		align-items: stretch;
		gap: 0.6rem;
		cursor: default;
	}

	.setting-label {
		font-size: 0.95rem;
		font-weight: 500;
	}

	.volume-row {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 1rem;
	}

	.volume-value {
		font-size: 0.95rem;
		color: var(--amber);
		font-variant-numeric: tabular-nums;
	}

	.volume-slider {
		width: 100%;
		accent-color: var(--amber);
		cursor: pointer;
	}

	.volume-slider:disabled {
		cursor: not-allowed;
		opacity: 0.45;
	}

	.setting-hint {
		margin: 0;
		font-size: 0.75rem;
		color: var(--text-dim);
		font-family: var(--font-mono);
		line-height: 1.4;
	}

	.toggle {
		position: relative;
		width: 44px;
		height: 24px;
		border-radius: 12px;
		background: var(--border);
		flex-shrink: 0;
		transition: background 0.2s, box-shadow 0.2s;
	}

	.toggle.active {
		background: var(--amber);
		box-shadow: 0 0 10px var(--amber-glow);
	}

	.toggle-knob {
		position: absolute;
		top: 2px;
		left: 2px;
		width: 20px;
		height: 20px;
		border-radius: 50%;
		background: var(--bg-deep);
		transition: transform 0.2s;
	}

	.toggle.active .toggle-knob {
		transform: translateX(20px);
	}
</style>
