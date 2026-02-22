import type { ClientMessage, ServerMessage } from './types';

export type MessageHandler = (message: ServerMessage) => void;
export type ConnectionState = 'disconnected' | 'connecting' | 'connected';
export type StateChangeHandler = (state: ConnectionState) => void;

export class YokeSocket {
	private ws: WebSocket | null = null;
	private handlers: MessageHandler[] = [];
	private openHandlers: Array<() => void> = [];
	private stateHandlers: StateChangeHandler[] = [];
	private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
	private pendingMessages: ClientMessage[] = [];
	private url: string;
	private _connectionState: ConnectionState = 'disconnected';

	constructor(url?: string) {
		const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
		// In dev mode, bypass the Vite proxy and connect directly to the backend port
		const backendPort = import.meta.env.PUBLIC_BACKEND_PORT;
		const host = backendPort
			? `${window.location.hostname}:${backendPort}`
			: window.location.host;
		this.url = url ?? `${protocol}//${host}/ws`;
	}

	get connectionState(): ConnectionState {
		return this._connectionState;
	}

	private setConnectionState(state: ConnectionState): void {
		if (this._connectionState === state) return;
		this._connectionState = state;
		for (const handler of this.stateHandlers) {
			handler(state);
		}
	}

	connect(): void {
		this.setConnectionState('connecting');
		this.ws = new WebSocket(this.url);

		this.ws.onopen = () => {
			this.setConnectionState('connected');

			for (const handler of this.openHandlers) {
				handler();
			}

			for (const msg of this.pendingMessages) {
				this.ws!.send(JSON.stringify(msg));
			}
			this.pendingMessages = [];
		};

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
			this.setConnectionState('connecting');
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
		this.setConnectionState('disconnected');
	}

	send(message: ClientMessage): void {
		if (this.ws && this.ws.readyState === WebSocket.OPEN) {
			this.ws.send(JSON.stringify(message));
		} else {
			this.pendingMessages.push(message);
		}
	}

	onMessage(handler: MessageHandler): () => void {
		this.handlers.push(handler);
		return () => {
			this.handlers = this.handlers.filter((h) => h !== handler);
		};
	}

	onOpen(handler: () => void): () => void {
		this.openHandlers.push(handler);
		return () => {
			this.openHandlers = this.openHandlers.filter((h) => h !== handler);
		};
	}

	onStateChange(handler: StateChangeHandler): () => void {
		this.stateHandlers.push(handler);
		return () => {
			this.stateHandlers = this.stateHandlers.filter((h) => h !== handler);
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
