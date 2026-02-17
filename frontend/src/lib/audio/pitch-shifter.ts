import { SoundTouch } from 'soundtouchjs';

const BUFFER_SIZE = 4096;

export class PitchShifter {
	private ctx: AudioContext | null = null;
	private source: MediaElementAudioSourceNode | null = null;
	private processor: ScriptProcessorNode | null = null;
	private st: SoundTouch | null = null;
	private connected = false;
	private semitones = 0;

	// Pre-allocated buffers to avoid GC pressure in audio callback
	private interleavedInput = new Float32Array(BUFFER_SIZE * 2);
	private interleavedOutput = new Float32Array(BUFFER_SIZE * 2);

	async connect(video: HTMLVideoElement): Promise<void> {
		if (this.connected) return;

		this.ctx = new AudioContext();
		this.source = this.ctx.createMediaElementSource(video);
		this.st = new SoundTouch();
		this.processor = this.ctx.createScriptProcessor(BUFFER_SIZE, 2, 2);

		this.processor.onaudioprocess = (e: AudioProcessingEvent) => {
			const inputL = e.inputBuffer.getChannelData(0);
			const inputR = e.inputBuffer.getChannelData(1);
			const outputL = e.outputBuffer.getChannelData(0);
			const outputR = e.outputBuffer.getChannelData(1);
			const numFrames = inputL.length;

			if (this.semitones === 0 || !this.st) {
				// Zero shift: passthrough without processing overhead
				outputL.set(inputL);
				outputR.set(inputR);
				return;
			}

			// Interleave stereo input: [L0, R0, L1, R1, ...]
			const inp = this.interleavedInput;
			for (let i = 0; i < numFrames; i++) {
				inp[i * 2] = inputL[i];
				inp[i * 2 + 1] = inputR[i];
			}

			// Feed samples to SoundTouch and process
			this.st.inputBuffer.putSamples(inp, 0, numFrames);
			this.st.process();

			// Read processed output
			const available = this.st.outputBuffer.frameCount;
			if (available >= numFrames) {
				this.st.outputBuffer.receiveSamples(this.interleavedOutput, numFrames);

				// De-interleave to output channels
				const out = this.interleavedOutput;
				for (let i = 0; i < numFrames; i++) {
					outputL[i] = out[i * 2];
					outputR[i] = out[i * 2 + 1];
				}
			} else {
				// Not enough output yet — output silence
				outputL.fill(0);
				outputR.fill(0);
			}
		};

		this.source.connect(this.processor);
		this.processor.connect(this.ctx.destination);
		this.connected = true;
	}

	setPitch(semitones: number): void {
		this.semitones = semitones;
		if (this.st) {
			this.st.pitchSemitones = semitones;
			if (semitones !== 0) {
				// Clear internal buffers when pitch changes to avoid artifacts
				this.st.clear();
			}
		}
	}

	async resume(): Promise<void> {
		if (this.ctx?.state === 'suspended') {
			await this.ctx.resume();
		}
	}

	disconnect(): void {
		this.processor?.disconnect();
		this.source?.disconnect();
		this.ctx?.close();
		this.processor = null;
		this.source = null;
		this.ctx = null;
		this.st = null;
		this.connected = false;
	}

	get isConnected(): boolean {
		return this.connected;
	}
}
