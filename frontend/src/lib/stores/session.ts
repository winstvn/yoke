import { writable } from 'svelte/store';
import type {
	Singer,
	QueueItem,
	PlaybackState,
	SessionSettings,
	Song,
	ServerMessage
} from '../types';
import { YokeSocket } from '../ws';

export const singers = writable<Singer[]>([]);
export const queue = writable<QueueItem[]>([]);
export const currentItem = writable<QueueItem | null>(null);
export const playback = writable<PlaybackState>({
	status: 'stopped',
	position_seconds: 0,
	pitch_shift: 0
});
export const settings = writable<SessionSettings>({
	host_id: null,
	anyone_can_reorder: false
});
export const searchResults = writable<Song[]>([]);
export const notifications = writable<Array<{ id: string; text: string }>>([]);
export const screenMessages = writable<Array<{ id: string; name: string; text: string }>>([]);
export const showQr = writable(false);

let socket: YokeSocket | null = null;

export function getSocket(): YokeSocket {
	if (!socket) {
		socket = new YokeSocket();
	}
	return socket;
}

export function addNotification(text: string): void {
	const id = crypto.randomUUID();
	notifications.update((n) => [...n, { id, text }]);
	setTimeout(() => {
		notifications.update((n) => n.filter((item) => item.id !== id));
	}, 4000);
}

export function initSession(sock: YokeSocket): void {
	sock.onMessage((msg: ServerMessage) => {
		switch (msg.type) {
			case 'state':
				singers.set(msg.singers);
				queue.set(msg.queue);
				currentItem.set(msg.current);
				playback.set(msg.playback);
				settings.set(msg.settings);
				break;

			case 'singer_joined':
				singers.update((s) => {
					const existing = s.find((singer) => singer.id === msg.singer.id);
					if (existing) {
						return s.map((singer) =>
							singer.id === msg.singer.id ? msg.singer : singer
						);
					}
					return [...s, msg.singer];
				});
				addNotification(`${msg.singer.name} joined`);
				break;

			case 'song_queued':
				addNotification(`${msg.item.singer.name} queued "${msg.item.song.title}"`);
				break;

			case 'queue_updated':
				queue.set(msg.queue);
				break;

			case 'playback_updated':
				playback.set(msg.playback);
				break;

			case 'download_progress':
				queue.update((q) =>
					q.map((item) =>
						item.song.video_id === msg.video_id
							? { ...item, status: 'downloading' as const }
							: item
					)
				);
				break;

			case 'search_results':
				searchResults.set(msg.songs);
				break;

			case 'settings_updated':
				settings.set(msg.settings);
				break;

			case 'show_qr':
				showQr.set(true);
				setTimeout(() => {
					showQr.set(false);
				}, 10000);
				break;

			case 'screen_message':
				screenMessages.update((msgs) => [
					...msgs,
					{ id: crypto.randomUUID(), name: msg.name, text: msg.text }
				]);
				break;

			case 'now_playing':
				currentItem.set(msg.item);
				addNotification(`Now playing: "${msg.item.song.title}"`);
				break;

			case 'up_next':
				addNotification(`Up next: ${msg.singer.name} — "${msg.song.title}"`);
				break;

			case 'error':
				addNotification(`Error: ${msg.message}`);
				break;
		}
	});
}
