<script lang="ts">
	import { onDestroy } from 'svelte';
	import { settings, getSocket } from '$lib/stores/session';
	import { get } from 'svelte/store';

	let { isHost = false, canControlVolume = false }: {
		isHost?: boolean;
		canControlVolume?: boolean;
	} = $props();

	const PENDING_TIMEOUT_MS = 2000;

	type AdminToggle =
		| 'anyone_can_reorder'
		| 'anyone_can_control_playback'
		| 'anyone_can_control_volume';

	let settingsValue = $state(get(settings));
	let localVolume = $state(get(settings).volume);
	// Value this singer has set but the server has not echoed back yet.
	let pending: number | null = $state(null);
	let sendTimer: ReturnType<typeof setTimeout> | null = null;
	let pendingTimer: ReturnType<typeof setTimeout> | null = null;

	$effect(() => {
		const unsub = settings.subscribe((val) => {
			settingsValue = val;
		});
		return () => {
			unsub();
		};
	});

	// Follow the server, so a change made on another phone shows up here. While
	// a local change is in flight, hold it instead -- otherwise the slider snaps
	// back to the old value until the broadcast lands.
	$effect(() => {
		const serverVolume = settingsValue.volume;
		if (pending === null) {
			localVolume = serverVolume;
		} else if (Math.abs(serverVolume - pending) < 1e-9) {
			clearPending();
		}
	});

	function clearPending() {
		pending = null;
		if (pendingTimer) {
			clearTimeout(pendingTimer);
			pendingTimer = null;
		}
	}

	function markPending(value: number) {
		pending = value;
		if (pendingTimer) clearTimeout(pendingTimer);
		// If the server never confirms (a rejected change, a dropped socket),
		// go back to following it rather than sticking on a value that never took.
		pendingTimer = setTimeout(clearPending, PENDING_TIMEOUT_MS);
	}

	function sendVolume(value: number) {
		markPending(value);
		getSocket().send({ type: 'update_setting', key: 'volume', value });
	}

	function handleVolumeInput(e: Event) {
		const value = Number((e.currentTarget as HTMLInputElement).value) / 100;
		localVolume = value;
		markPending(value);
		// Throttle while dragging; every send fans out to all clients.
		if (sendTimer) return;
		sendTimer = setTimeout(() => {
			sendTimer = null;
			sendVolume(localVolume);
		}, 100);
	}

	function handleVolumeCommit() {
		// Read before anything else can reconcile against the server value.
		const value = localVolume;
		if (sendTimer) {
			clearTimeout(sendTimer);
			sendTimer = null;
		}
		sendVolume(value);
	}

	function toggleAdmin(key: AdminToggle) {
		if (!isHost) return;
		getSocket().send({ type: 'update_setting', key, value: !settingsValue[key] });
	}

	onDestroy(() => {
		if (sendTimer) clearTimeout(sendTimer);
		if (pendingTimer) clearTimeout(pendingTimer);
	});
</script>

<div class="settings-tab">
	<h2 class="settings-heading">Settings</h2>

	<section class="setting-group">
		<h3 class="group-heading">Audio</h3>
		<div class="setting-card setting-card-static">
			<div class="volume-row">
				<span class="setting-label">Music Volume</span>
				<span class="volume-value">{Math.round(localVolume * 100)}%</span>
			</div>
			<input
				type="range"
				class="volume-slider"
				min="0"
				max="100"
				step="1"
				value={Math.round(localVolume * 100)}
				disabled={!canControlVolume}
				oninput={handleVolumeInput}
				onchange={handleVolumeCommit}
				aria-label="Music Volume"
			/>
		</div>
	</section>

	{#if isHost}
		<section class="setting-group">
			<h3 class="group-heading">Admin</h3>

			<button class="setting-card" onclick={() => toggleAdmin('anyone_can_reorder')}>
				<span class="setting-label">Allow everyone to reorder the queue</span>
				<span class="toggle" class:active={settingsValue.anyone_can_reorder}>
					<span class="toggle-knob"></span>
				</span>
			</button>

			<button class="setting-card" onclick={() => toggleAdmin('anyone_can_control_playback')}>
				<span class="setting-label">Allow everyone to control playback and pitch</span>
				<span class="toggle" class:active={settingsValue.anyone_can_control_playback}>
					<span class="toggle-knob"></span>
				</span>
			</button>

			<button class="setting-card" onclick={() => toggleAdmin('anyone_can_control_volume')}>
				<span class="setting-label">Allow everyone to control the volume</span>
				<span class="toggle" class:active={settingsValue.anyone_can_control_volume}>
					<span class="toggle-knob"></span>
				</span>
			</button>
		</section>
	{/if}
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

	.setting-card:hover {
		background: var(--bg-surface-hover);
	}

	.setting-card-static {
		display: flex;
		flex-direction: column;
		align-items: stretch;
		gap: 0.6rem;
		cursor: default;
	}

	.setting-card-static:hover {
		background: var(--bg-surface);
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
