<script lang="ts">
	import { queue, currentItem, settings, getSocket } from '$lib/stores/session';
	import { get } from 'svelte/store';
	import type { QueueItem, SessionSettings } from '$lib/types';

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

	function statusLabel(status: QueueItem['status']): string {
		switch (status) {
			case 'waiting':
				return 'Waiting';
			case 'downloading':
				return 'Downloading...';
			case 'ready':
				return 'Ready';
			case 'playing':
				return 'Playing';
			case 'done':
				return 'Done';
			default:
				return status;
		}
	}

	function statusClass(status: QueueItem['status']): string {
		switch (status) {
			case 'waiting':
				return 'badge-waiting';
			case 'downloading':
				return 'badge-downloading';
			case 'ready':
				return 'badge-ready';
			case 'playing':
				return 'badge-playing';
			default:
				return 'badge-waiting';
		}
	}

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
				<span class="badge badge-playing">Playing</span>
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
						<span class="badge {statusClass(item.status)}">{statusLabel(item.status)}</span>
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
		color: #888;
	}

	.now-playing-card {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border-radius: 8px;
		border: 1px solid #5555ff;
		background: #1a1a40;
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
		border-radius: 8px;
		border: 1px solid #333;
		background: #1a1a2e;
		transition: background 0.15s;
	}

	.queue-card.is-playing {
		border-color: #5555ff;
		background: #1a1a40;
	}

	.queue-card.drag-over {
		border-color: #5555ff;
		background: #22224e;
	}

	.queue-card.dragging {
		opacity: 0.4;
	}

	/* Drag handle */
	.drag-handle {
		cursor: grab;
		color: #555;
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
	}

	.singer-name {
		font-size: 0.8rem;
		color: #888;
	}

	/* Actions */
	.card-actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-shrink: 0;
	}

	/* Status badges */
	.badge {
		font-size: 0.7rem;
		font-weight: 600;
		padding: 0.15rem 0.5rem;
		border-radius: 4px;
		white-space: nowrap;
	}

	.badge-waiting {
		background: #444;
		color: #ccc;
	}

	.badge-downloading {
		background: #a855f7;
		color: #fff;
	}

	.badge-ready {
		background: #22c55e;
		color: #000;
	}

	.badge-playing {
		background: #5555ff;
		color: #fff;
	}

	/* Remove button */
	.remove-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.75rem;
		height: 1.75rem;
		border-radius: 6px;
		border: 1px solid #444;
		background: transparent;
		color: #888;
		font-size: 1.1rem;
		cursor: pointer;
		line-height: 1;
		padding: 0;
	}

	.remove-btn:hover {
		background: #ff4444;
		border-color: #ff4444;
		color: #fff;
	}

	/* Empty state */
	.empty-state {
		color: #666;
		text-align: center;
		margin-top: 3rem;
		font-size: 1rem;
	}
</style>
