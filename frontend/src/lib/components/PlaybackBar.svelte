<script lang="ts">
	import { playback, currentItem, getSocket } from '$lib/stores/session';
	import { get } from 'svelte/store';

	let playbackState = $state(get(playback));
	let current = $state(get(currentItem));

	$effect(() => {
		const unsubPlayback = playback.subscribe((val) => {
			playbackState = val;
		});
		const unsubCurrent = currentItem.subscribe((val) => {
			current = val;
		});
		return () => {
			unsubPlayback();
			unsubCurrent();
		};
	});

	let seeking = $state(false);
	let seekValue = $state(0);

	let displayPosition = $derived(seeking ? seekValue : playbackState.position_seconds);
	let duration = $derived(current?.song.duration_seconds ?? 0);

	function sendPlayback(action: 'play' | 'pause' | 'stop' | 'skip' | 'restart') {
		getSocket().send({ type: 'playback', action });
	}

	function handleSeekInput(e: Event) {
		const target = e.target as HTMLInputElement;
		seeking = true;
		seekValue = Number(target.value);
	}

	function handleSeekChange(e: Event) {
		const target = e.target as HTMLInputElement;
		const position = Number(target.value);
		getSocket().send({ type: 'seek', position_seconds: position });
		seeking = false;
	}

	function handlePitch(delta: number) {
		getSocket().send({ type: 'pitch', semitones: playbackState.pitch_shift + delta });
	}

	function resetPitch() {
		getSocket().send({ type: 'pitch', semitones: 0 });
	}

	function formatTime(seconds: number): string {
		const m = Math.floor(seconds / 60);
		const s = Math.floor(seconds % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	let pitchDisplay = $derived(
		playbackState.pitch_shift > 0
			? `Pitch: +${playbackState.pitch_shift}`
			: `Pitch: ${playbackState.pitch_shift}`
	);
</script>

<div class="playback-bar">
	{#if current}
		<div class="now-playing">
			<span class="song-title">{current.song.title}</span>
			<span class="singer-name">{current.singer.name}</span>
		</div>
	{/if}

	<div class="controls">
		{#if playbackState.status === 'playing'}
			<button class="ctrl-btn" onclick={() => sendPlayback('pause')} title="Pause">&#10074;&#10074;</button>
		{:else}
			<button class="ctrl-btn" onclick={() => sendPlayback('play')} title="Play">&#9654;</button>
		{/if}
		<button class="ctrl-btn" onclick={() => sendPlayback('stop')} title="Stop">&#9632;</button>
		<button class="ctrl-btn" onclick={() => sendPlayback('skip')} title="Skip">&#9197;</button>
		<button class="ctrl-btn" onclick={() => sendPlayback('restart')} title="Restart">&#8634;</button>
	</div>

	{#if current}
		<div class="seek-row">
			<span class="time">{formatTime(displayPosition)}</span>
			<input
				type="range"
				class="seek-bar"
				min="0"
				max={duration}
				value={displayPosition}
				oninput={handleSeekInput}
				onchange={handleSeekChange}
			/>
			<span class="time">{formatTime(duration)}</span>
		</div>
	{/if}

	<div class="pitch-row">
		<button class="pitch-btn" onclick={() => handlePitch(-1)}>-</button>
		<span class="pitch-display">{pitchDisplay}</span>
		<button class="pitch-btn" onclick={() => handlePitch(1)}>+</button>
		{#if playbackState.pitch_shift !== 0}
			<button class="pitch-reset" onclick={resetPitch}>Reset</button>
		{/if}
	</div>
</div>

<style>
	.playback-bar {
		position: fixed;
		bottom: 0;
		left: 0;
		right: 0;
		z-index: 100;
		background: #1a1a2e;
		border-top: 1px solid #333;
		padding: 0.75rem 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.now-playing {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 0.5rem;
	}

	.song-title {
		color: white;
		font-size: 0.9rem;
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		flex: 1;
	}

	.singer-name {
		color: #888;
		font-size: 0.85rem;
		flex-shrink: 0;
	}

	.controls {
		display: flex;
		justify-content: center;
		gap: 0.75rem;
	}

	.ctrl-btn {
		width: 40px;
		height: 40px;
		border-radius: 50%;
		border: 1px solid #444;
		background: transparent;
		color: white;
		font-size: 1rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.ctrl-btn:hover {
		background: #2a2a4e;
	}

	.seek-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.time {
		color: #888;
		font-size: 0.75rem;
		min-width: 3rem;
		text-align: center;
	}

	.seek-bar {
		flex: 1;
		accent-color: #5555ff;
		height: 4px;
	}

	.pitch-row {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
	}

	.pitch-btn {
		width: 30px;
		height: 30px;
		border-radius: 50%;
		border: 1px solid #444;
		background: transparent;
		color: white;
		font-size: 1rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.pitch-btn:hover {
		background: #2a2a4e;
	}

	.pitch-display {
		color: #ccc;
		font-size: 0.85rem;
		min-width: 5rem;
		text-align: center;
	}

	.pitch-reset {
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		border: 1px solid #444;
		background: transparent;
		color: #aaa;
		font-size: 0.75rem;
		cursor: pointer;
	}

	.pitch-reset:hover {
		background: #2a2a4e;
	}
</style>
