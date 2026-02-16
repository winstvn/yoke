<script lang="ts">
	type BadgeVariant = 'downloaded' | 'waiting' | 'downloading' | 'queued' | 'playing';

	let { variant, label }: { variant: BadgeVariant; label?: string } = $props();

	const defaults: Record<BadgeVariant, string> = {
		downloaded: 'Downloaded',
		waiting: 'Waiting',
		downloading: 'Downloading',
		queued: 'Queued',
		playing: 'Playing'
	};
</script>

<span class="badge badge-{variant}">{label ?? defaults[variant]}</span>

<style>
	.badge {
		font-size: 0.7rem;
		font-weight: 600;
		padding: 0.15rem 0.5rem;
		border-radius: 2px;
		white-space: nowrap;
		font-family: var(--font-mono);
	}

	.badge-downloaded {
		background: var(--amber-bright);
		color: var(--bg-deep);
	}

	.badge-waiting {
		background: var(--amber-dim);
		color: var(--text-primary);
	}

	.badge-downloading {
		background: var(--amber);
		color: var(--bg-deep);
		animation: glow-pulse 1.5s ease-in-out infinite;
	}

	.badge-queued {
		background: var(--amber);
		color: var(--bg-deep);
	}

	.badge-playing {
		background: var(--amber-bright);
		color: var(--bg-deep);
		box-shadow: 0 0 8px var(--amber-glow-strong);
	}
</style>
