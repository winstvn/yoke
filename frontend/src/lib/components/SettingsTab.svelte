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
		color: white;
		margin: 0;
	}

	.setting-card {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 1rem;
		border-radius: 8px;
		border: 1px solid #333;
		background: #1a1a2e;
		cursor: pointer;
		width: 100%;
		text-align: left;
		color: white;
	}

	.setting-card:hover {
		background: #2a2a4e;
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
		background: #444;
		flex-shrink: 0;
		transition: background 0.2s;
	}

	.toggle.active {
		background: #5555ff;
	}

	.toggle-knob {
		position: absolute;
		top: 2px;
		left: 2px;
		width: 20px;
		height: 20px;
		border-radius: 50%;
		background: white;
		transition: transform 0.2s;
	}

	.toggle.active .toggle-knob {
		transform: translateX(20px);
	}
</style>
