<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { PitchShifter } from '$lib/audio/pitch-shifter';
	import { playbackGain } from '$lib/audio/loudness';
	import { playback, currentItem, settings, getSocket } from '$lib/stores/session';
	import { get } from 'svelte/store';

	let playbackState = $state(get(playback));
	let current = $state(get(currentItem));
	let settingsValue = $state(get(settings));

	$effect(() => {
		const unsubPlayback = playback.subscribe((val) => {
			playbackState = val;
		});
		const unsubCurrent = currentItem.subscribe((val) => {
			current = val;
		});
		const unsubSettings = settings.subscribe((val) => {
			settingsValue = val;
		});
		return () => {
			unsubPlayback();
			unsubCurrent();
			unsubSettings();
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

	// Loudness normalization for this song, scaled by the session volume.
	$effect(() => {
		const song = current?.song;
		pitchShifter?.setGain(
			playbackGain(song?.loudness_lufs ?? null, song?.true_peak_db ?? null, settingsValue.volume)
		);
	});

	// Watch for current item changes - load new video
	$effect(() => {
		const item = current;
		if (!videoEl) return;

		if (item && item.song.video_id !== lastVideoId) {
			lastVideoId = item.song.video_id;
			videoEl.src = `/videos/${item.song.video_id}`;
			videoEl.load();
			videoEl
				.play()
				.then(async () => {
					if (!pitchShifter.isConnected) {
						await pitchShifter.connect(videoEl);
					}
					await pitchShifter.resume();
					pitchShifter.setPitch(playbackState.pitch_shift);
				})
				// A missing/undecodable source rejects here as well as firing the
				// element's `error` event; onError drives the recovery.
				.catch((err) => console.error('Playback failed to start:', err));
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
		if (!videoEl) return;
		const diff = Math.abs(videoEl.currentTime - serverPosition);
		if (diff > 2) {
			videoEl.currentTime = serverPosition;
		}
	});

	function onEnded() {
		// The display is a passive renderer and never "joins" as a singer, so it
		// can't use the permission-gated `skip` action. A natural end-of-video is
		// an automatic event, not a user control — signal it as its own message.
		getSocket().send({ type: 'song_ended', item_id: current?.id });
	}

	function onError() {
		// A video that fails to load (e.g. the file was never downloaded, so
		// /videos/{id} 404s) never fires `ended`, which would leave the display
		// black forever. Treat it as the end of the song so the queue advances.
		console.error('Video failed to load:', current?.song.video_id, videoEl?.error);
		getSocket().send({ type: 'song_ended', item_id: current?.id });
	}
</script>

<video
	bind:this={videoEl}
	class="video-player"
	onended={onEnded}
	onerror={onError}
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
