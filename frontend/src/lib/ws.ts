import type { ClientMessage, ServerMessage } from './types';

export type MessageHandler = (message: ServerMessage) => void;

export class YokeSocket {
	private ws: WebSocket | null = null;
	private handlers: MessageHandler[] = [];
	private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
	private url: string;

	constructor(url?: string) {
		const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
		this.url = url ?? `${protocol}//${window.location.host}/ws`;
	}

	connect(): void {
		this.ws = new WebSocket(this.url);

		this.ws.onmessage = (event: MessageEvent) => {
			try {
				const message: ServerMessage = JSON.parse(event.data);
				for (const handler of this.handlers) {
					handler(message);
				}
			} catch {
				console.error('Failed to parse WebSocket message:', event.data);
			}
		};

		this.ws.onclose = () => {
			this.ws = null;
			this.scheduleReconnect();
		};

		this.ws.onerror = (error: Event) => {
			console.error('WebSocket error:', error);
		};
	}

	disconnect(): void {
		if (this.reconnectTimer !== null) {
			clearTimeout(this.reconnectTimer);
			this.reconnectTimer = null;
		}
		if (this.ws) {
			this.ws.onclose = null;
			this.ws.close();
			this.ws = null;
		}
	}

	send(message: ClientMessage): void {
		if (this.ws && this.ws.readyState === WebSocket.OPEN) {
			this.ws.send(JSON.stringify(message));
		}
	}

	onMessage(handler: MessageHandler): () => void {
		this.handlers.push(handler);
		return () => {
			this.handlers = this.handlers.filter((h) => h !== handler);
		};
	}

	private scheduleReconnect(): void {
		if (this.reconnectTimer !== null) return;
		this.reconnectTimer = setTimeout(() => {
			this.reconnectTimer = null;
			this.connect();
		}, 2000);
	}
}
