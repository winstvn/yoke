<script lang="ts">
	import { searchResults, searchQuery, queue, currentItem, getSocket } from '$lib/stores/session';
	import { get } from 'svelte/store';
	import type { Song, QueueItem } from '$lib/types';
	import StatusBadge from './StatusBadge.svelte';

	let query = $state(get(searchQuery));
	let searching = $state(false);
	let results = $state<Song[]>(get(searchResults));
	let queueItems = $state<QueueItem[]>(get(queue));
	let current = $state<QueueItem | null>(get(currentItem));
	let queuedStatus = $derived(() => {
		const map = new Map(queueItems.map((item) => [item.song.video_id, item.status]));
		if (current) {
			map.set(current.song.video_id, 'playing');
		}
		return map;
	});

	$effect(() => {
		const unsub = searchResults.subscribe((val) => {
			results = val;
			searching = false;
		});
		return () => {
			unsub();
		};
	});

	$effect(() => {
		const unsub = queue.subscribe((val) => {
			queueItems = val;
		});
		return () => {
			unsub();
		};
	});

	$effect(() => {
		const unsub = currentItem.subscribe((val) => {
			current = val;
		});
		return () => {
			unsub();
		};
	});

	$effect(() => {
		searchQuery.set(query);
	});

	function handleSearch(e: Event) {
		e.preventDefault();
		const trimmed = query.trim();
		if (!trimmed) return;
		searching = true;
		getSocket().send({ type: 'search', query: trimmed });
	}

	function queueSong(videoId: string) {
		getSocket().send({ type: 'queue_song', video_id: videoId });
	}

	function formatDuration(seconds: number): string {
		return Math.floor(seconds / 60) + ':' + (seconds % 60).toString().padStart(2, '0');
	}
</script>

<div class="search-tab">
	<form class="search-form" onsubmit={handleSearch}>
		<input
			type="text"
			class="search-input"
			placeholder="Search for a song..."
			bind:value={query}
		/>
		<button type="submit" class="search-btn" disabled={searching || !query.trim()}>
			{searching ? 'Searching...' : 'Search'}
		</button>
	</form>

	<div class="results">
		{#each results as song (song.video_id)}
			{@const status = queuedStatus().get(song.video_id)}
			<button class="song-card" class:song-card-queued={!!status} onclick={() => queueSong(song.video_id)}>
				<img
					class="thumbnail"
					src={song.thumbnail_url}
					alt={song.title}
					width="80"
					height="60"
				/>
				<div class="song-info">
					<span class="song-title">{song.title}</span>
					<div class="song-meta">
						<span class="duration">{formatDuration(song.duration_seconds)}</span>
						{#if song.cached || status === 'ready' || status === 'playing' || status === 'done'}
							<StatusBadge variant="downloaded" />
						{/if}
						{#if status === 'waiting'}
							<StatusBadge variant="waiting" />
						{:else if status === 'downloading'}
							<StatusBadge variant="downloading" />
						{:else if status === 'ready'}
							<StatusBadge variant="queued" />
						{:else if status === 'playing'}
							<StatusBadge variant="playing" />
						{/if}
					</div>
				</div>
			</button>
		{/each}
	</div>
</div>

<style>
	.search-tab {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.search-form {
		display: flex;
		gap: 0.5rem;
	}

	.search-input {
		flex: 1;
		padding: 0.75rem 1rem;
		border-radius: 8px;
		border: 1px solid #333;
		background: #1a1a2e;
		color: white;
		font-size: 1rem;
		outline: none;
	}

	.search-input::placeholder {
		color: #666;
	}

	.search-input:focus {
		border-color: #5555ff;
	}

	.search-btn {
		padding: 0.75rem 1.25rem;
		border-radius: 8px;
		border: 1px solid #5555ff;
		background: #5555ff;
		color: white;
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
		white-space: nowrap;
	}

	.search-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.search-btn:not(:disabled):hover {
		background: #4444dd;
	}

	.results {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		overflow-y: auto;
	}

	.song-card {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.5rem;
		border-radius: 8px;
		border: 1px solid #333;
		background: #1a1a2e;
		cursor: pointer;
		text-align: left;
		color: white;
		width: 100%;
	}

	.song-card:hover {
		background: #2a2a4e;
	}

	.thumbnail {
		border-radius: 4px;
		object-fit: cover;
		flex-shrink: 0;
	}

	.song-info {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		min-width: 0;
		flex: 1;
	}

	.song-title {
		font-size: 0.9rem;
		font-weight: 500;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.song-meta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.duration {
		color: #888;
		font-size: 0.8rem;
	}

	.song-card-queued {
		opacity: 0.5;
	}
</style>
