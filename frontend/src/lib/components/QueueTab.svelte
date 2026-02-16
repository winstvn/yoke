<script lang="ts">
	import { queue, currentItem, settings, getSocket } from '$lib/stores/session';
	import { get } from 'svelte/store';
	import type { QueueItem, SessionSettings } from '$lib/types';
	import StatusBadge from './StatusBadge.svelte';

	let { singerId, isHost }: { singerId: string; isHost: boolean } = $props();

	let items = $state<QueueItem[]>(get(queue));
	let current = $state<QueueItem | null>(get(currentItem));
	let settingsValue = $state<SessionSettings>(get(settings));

	$effect(() => {
		const unsubQueue = queue.subscribe((val) => {
			items = val;
		});
		return () => {
			unsubQueue();
		};
	});

	$effect(() => {
		const unsubCurrent = currentItem.subscribe((val) => {
			current = val;
		});
		return () => {
			unsubCurrent();
		};
	});

	$effect(() => {
		const unsubSettings = settings.subscribe((val) => {
			settingsValue = val;
		});
		return () => {
			unsubSettings();
		};
	});

	let canReorder = $derived(isHost || settingsValue.anyone_can_reorder);

	let dragIndex = $state<number | null>(null);
	let dragOverIndex = $state<number | null>(null);

	const statusVariant: Record<QueueItem['status'], 'waiting' | 'downloading' | 'queued' | 'playing' | 'downloaded'> = {
		waiting: 'waiting',
		downloading: 'downloading',
		ready: 'queued',
		playing: 'playing',
		done: 'downloaded'
	};

	function canRemove(item: QueueItem): boolean {
		return isHost || item.singer.id === singerId;
	}

	function removeItem(itemId: string) {
		getSocket().send({ type: 'remove_from_queue', item_id: itemId });
	}

	function handleDragStart(e: DragEvent, index: number) {
		if (!canReorder) return;
		dragIndex = index;
		if (e.dataTransfer) {
			e.dataTransfer.effectAllowed = 'move';
			e.dataTransfer.setData('text/plain', String(index));
		}
	}

	function handleDragOver(e: DragEvent, index: number) {
		if (!canReorder || dragIndex === null) return;
		e.preventDefault();
		if (e.dataTransfer) {
			e.dataTransfer.dropEffect = 'move';
		}
		dragOverIndex = index;
	}

	function handleDragLeave() {
		dragOverIndex = null;
	}

	function handleDrop(e: DragEvent, dropIndex: number) {
		e.preventDefault();
		if (!canReorder || dragIndex === null || dragIndex === dropIndex) {
			dragIndex = null;
			dragOverIndex = null;
			return;
		}

		const reordered = [...items];
		const [moved] = reordered.splice(dragIndex, 1);
		reordered.splice(dropIndex, 0, moved);

		getSocket().send({ type: 'reorder_queue', item_ids: reordered.map((item) => item.id) });

		dragIndex = null;
		dragOverIndex = null;
	}

	function handleDragEnd() {
		dragIndex = null;
		dragOverIndex = null;
	}
</script>

<div class="queue-tab">
	{#if current}
		<div class="now-playing">
			<div class="now-playing-label">Now Playing</div>
			<div class="now-playing-card">
				<div class="song-details">
					<span class="song-title">{current.song.title}</span>
					<span class="singer-name">{current.singer.name}</span>
				</div>
				<StatusBadge variant="playing" />
			</div>
		</div>
	{/if}

	{#if items.length === 0}
		<p class="empty-state">Queue is empty. Search for songs to add!</p>
	{:else}
		<div class="queue-list">
			{#each items as item, index (item.id)}
				<div
					class="queue-card"
					class:is-playing={current?.id === item.id}
					class:drag-over={dragOverIndex === index && dragIndex !== index}
					class:dragging={dragIndex === index}
					draggable={canReorder}
					ondragstart={(e) => handleDragStart(e, index)}
					ondragover={(e) => handleDragOver(e, index)}
					ondragleave={handleDragLeave}
					ondrop={(e) => handleDrop(e, index)}
					ondragend={handleDragEnd}
					role="listitem"
				>
					{#if canReorder}
						<span class="drag-handle" aria-label="Drag to reorder">&#x2630;</span>
					{/if}
					<div class="song-details">
						<span class="song-title">{item.song.title}</span>
						<span class="singer-name">{item.singer.name}</span>
					</div>
					<div class="card-actions">
						<StatusBadge variant={statusVariant[item.status]} />
						{#if canRemove(item)}
							<button
								class="remove-btn"
								onclick={() => removeItem(item.id)}
								aria-label="Remove {item.song.title} from queue"
							>
								&times;
							</button>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.queue-tab {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	/* Now playing */
	.now-playing {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.now-playing-label {
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-secondary);
	}

	.now-playing-card {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border-radius: 4px;
		border: 1px solid var(--border-bright);
		background: var(--bg-surface);
		box-shadow: 0 0 12px var(--amber-glow);
	}

	/* Queue list */
	.queue-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		overflow-y: auto;
	}

	.queue-card {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.6rem 0.75rem;
		border-radius: 4px;
		border: 1px solid var(--border);
		background: var(--bg-surface);
		transition: background 0.15s, border-color 0.15s;
	}

	.queue-card.is-playing {
		border-color: var(--border-bright);
		background: var(--bg-surface);
		box-shadow: 0 0 10px var(--amber-glow);
	}

	.queue-card.drag-over {
		border-color: var(--amber-bright);
		background: var(--bg-surface-hover);
	}

	.queue-card.dragging {
		opacity: 0.4;
	}

	/* Drag handle */
	.drag-handle {
		cursor: grab;
		color: var(--amber-dim);
		font-size: 1rem;
		user-select: none;
		flex-shrink: 0;
		line-height: 1;
	}

	.drag-handle:active {
		cursor: grabbing;
	}

	/* Song details */
	.song-details {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		min-width: 0;
		flex: 1;
	}

	.song-title {
		font-size: 0.9rem;
		font-weight: 500;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		color: var(--text-primary);
	}

	.singer-name {
		font-size: 0.8rem;
		color: var(--text-secondary);
	}

	/* Actions */
	.card-actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-shrink: 0;
	}

	/* Remove button */
	.remove-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.75rem;
		height: 1.75rem;
		border-radius: 4px;
		border: 1px solid var(--border);
		background: transparent;
		color: var(--text-secondary);
		font-size: 1.1rem;
		cursor: pointer;
		line-height: 1;
		padding: 0;
	}

	.remove-btn:hover {
		background: var(--danger);
		border-color: var(--danger);
		color: #fff;
	}

	/* Empty state */
	.empty-state {
		color: var(--text-dim);
		text-align: center;
		margin-top: 3rem;
		font-size: 1rem;
	}
</style>
