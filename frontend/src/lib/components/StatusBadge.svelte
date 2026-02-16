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
		border-radius: 4px;
		white-space: nowrap;
	}

	.badge-downloaded {
		background: #22c55e;
		color: #000;
	}

	.badge-waiting {
		background: #6b7280;
		color: #fff;
	}

	.badge-downloading {
		background: #f59e0b;
		color: #000;
	}

	.badge-queued {
		background: #3b82f6;
		color: #fff;
	}

	.badge-playing {
		background: #a855f7;
		color: #fff;
	}
</style>
