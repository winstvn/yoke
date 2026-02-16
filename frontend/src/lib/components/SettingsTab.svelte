<script lang="ts">
	import { settings, getSocket } from '$lib/stores/session';
	import { get } from 'svelte/store';

	let settingsValue = $state(get(settings));

	$effect(() => {
		const unsub = settings.subscribe((val) => {
			settingsValue = val;
		});
		return () => {
			unsub();
		};
	});

	function toggleReorder() {
		getSocket().send({
			type: 'update_setting',
			key: 'anyone_can_reorder',
			value: !settingsValue.anyone_can_reorder
		});
	}
</script>

<div class="settings-tab">
	<h2 class="settings-heading">Settings</h2>

	<button class="setting-card" onclick={toggleReorder}>
		<span class="setting-label">Allow everyone to reorder the queue</span>
		<span class="toggle" class:active={settingsValue.anyone_can_reorder}>
			<span class="toggle-knob"></span>
		</span>
	</button>
</div>

<style>
	.settings-tab {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.settings-heading {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--amber);
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

	.setting-label {
		font-size: 0.95rem;
		font-weight: 500;
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
