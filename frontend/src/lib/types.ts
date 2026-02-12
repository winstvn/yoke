export interface Singer {
	id: string;
	name: string;
	connected: boolean;
}

export interface Song {
	video_id: string;
	title: string;
	thumbnail_url: string;
	duration_seconds: number;
	cached: boolean;
}

export interface QueueItem {
	id: string;
	song: Song;
	singer: Singer;
	status: 'waiting' | 'downloading' | 'ready' | 'playing' | 'done';
}

export interface PlaybackState {
	status: 'playing' | 'paused' | 'stopped';
	position_seconds: number;
	pitch_shift: number;
}

export interface SessionSettings {
	host_id: string | null;
	anyone_can_reorder: boolean;
}

export interface SessionState {
	singers: Singer[];
	queue: QueueItem[];
	current: QueueItem | null;
	playback: PlaybackState;
	settings: SessionSettings;
}

// Server -> Client message types
export type ServerMessage =
	| ({ type: 'state' } & SessionState)
	| { type: 'singer_joined'; singer: Singer }
	| { type: 'song_queued'; item: QueueItem; singer: Singer }
	| { type: 'queue_updated'; queue: QueueItem[] }
	| { type: 'playback_updated'; playback: PlaybackState }
	| { type: 'download_progress'; video_id: string; percent: number }
	| { type: 'search_results'; songs: Song[] }
	| { type: 'show_qr' }
	| { type: 'screen_message'; name: string; text: string }
	| { type: 'now_playing'; item: QueueItem }
	| { type: 'up_next'; singer: Singer; song: Song }
	| { type: 'error'; message: string };

// Client -> Server message types
export type ClientMessage =
	| { type: 'join'; name: string }
	| { type: 'search'; query: string }
	| { type: 'queue_song'; video_id: string }
	| { type: 'remove_from_queue'; item_id: string }
	| { type: 'reorder_queue'; item_ids: string[] }
	| { type: 'playback'; action: 'play' | 'pause' | 'stop' | 'skip' | 'restart' }
	| { type: 'seek'; position_seconds: number }
	| { type: 'pitch'; semitones: number }
	| { type: 'update_setting'; key: string; value: unknown }
	| { type: 'show_qr' }
	| { type: 'screen_message'; text: string }
	| { type: 'position_update'; position_seconds: number };
