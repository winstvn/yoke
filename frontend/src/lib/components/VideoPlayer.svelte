<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { PitchShifter } from '$lib/audio/pitch-shifter';
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

	let videoEl: HTMLVideoElement;
	let pitchShifter: PitchShifter;
	let positionInterval: ReturnType<typeof setInterval>;
	let lastVideoId: string | null = null;

	onMount(() => {
		pitchShifter = new PitchShifter();

		// Report position to server every second
		positionInterval = setInterval(() => {
			if (videoEl && !videoEl.paused) {
				getSocket().send({
					type: 'position_update',
					position_seconds: videoEl.currentTime
				});
			}
		}, 1000);
	});

	onDestroy(() => {
		clearInterval(positionInterval);
		pitchShifter?.disconnect();
	});

	// Watch for current item changes - load new video
	$effect(() => {
		const item = current;
		if (!videoEl) return;

		if (item && item.song.video_id !== lastVideoId) {
			lastVideoId = item.song.video_id;
			videoEl.src = `/videos/${item.song.video_id}`;
			videoEl.load();
			videoEl.play().then(async () => {
				if (!pitchShifter.isConnected) {
					await pitchShifter.connect(videoEl);
				}
				await pitchShifter.resume();
				pitchShifter.setPitch(playbackState.pitch_shift);
			});
		} else if (!item) {
			lastVideoId = null;
			videoEl.removeAttribute('src');
			videoEl.load();
		}
	});

	// Watch for playback state changes
	$effect(() => {
		const state = playbackState;
		if (!videoEl) return;

		if (state.status === 'playing') {
			if (videoEl.paused && videoEl.src) {
				videoEl.play().then(async () => {
					await pitchShifter?.resume();
				});
			}
		} else if (state.status === 'paused') {
			if (!videoEl.paused) {
				videoEl.pause();
			}
		} else if (state.status === 'stopped') {
			videoEl.pause();
			videoEl.currentTime = 0;
		}

		// Apply pitch shift
		pitchShifter?.setPitch(state.pitch_shift);
	});

	// Handle seek: if server position differs from video by >2 seconds, seek
	$effect(() => {
		const serverPosition = playbackState.position_seconds;
		if (!videoEl || videoEl.paused) return;
		const diff = Math.abs(videoEl.currentTime - serverPosition);
		if (diff > 2) {
			videoEl.currentTime = serverPosition;
		}
	});

	function onEnded() {
		getSocket().send({ type: 'playback', action: 'skip' });
	}
</script>

<video
	bind:this={videoEl}
	class="video-player"
	onended={onEnded}
	playsinline
	crossorigin="anonymous"
></video>

<style>
	.video-player {
		width: 100vw;
		height: 100vh;
		object-fit: contain;
		background: black;
	}
</style>
