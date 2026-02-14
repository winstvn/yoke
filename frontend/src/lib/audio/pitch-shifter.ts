export class PitchShifter {
	private ctx: AudioContext | null = null;
	private source: MediaElementAudioSourceNode | null = null;
	private videoElement: HTMLVideoElement | null = null;
	private connected = false;

	async connect(video: HTMLVideoElement): Promise<void> {
		if (this.connected) return;
		this.videoElement = video;
		this.ctx = new AudioContext();
		this.source = this.ctx.createMediaElementSource(video);
		this.source.connect(this.ctx.destination);
		this.connected = true;
	}

	setPitch(semitones: number): void {
		if (!this.videoElement) return;
		// Simple approach: change playbackRate to shift pitch
		// 2^(semitones/12) gives the frequency ratio
		const rate = Math.pow(2, semitones / 12);
		this.videoElement.playbackRate = rate;
	}

	async resume(): Promise<void> {
		if (this.ctx?.state === 'suspended') {
			await this.ctx.resume();
		}
	}

	disconnect(): void {
		this.source?.disconnect();
		this.ctx?.close();
		this.source = null;
		this.ctx = null;
		this.videoElement = null;
		this.connected = false;
	}

	get isConnected(): boolean {
		return this.connected;
	}
}
