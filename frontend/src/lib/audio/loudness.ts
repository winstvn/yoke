// Keep in step with backend/src/yoke/loudness.py.
export const TARGET_LUFS = -14;
export const PEAK_CEILING_DBTP = -1;

/**
 * dB of gain that brings a track to TARGET_LUFS, capped so its peaks stay
 * under PEAK_CEILING_DBTP. Unmeasured tracks get 0 (no normalization).
 */
export function normalizationGainDb(
	loudnessLufs: number | null,
	truePeakDb: number | null
): number {
	if (loudnessLufs === null || !Number.isFinite(loudnessLufs)) return 0;

	const wanted = TARGET_LUFS - loudnessLufs;

	// Without a peak reading there is no way to know how much boost is safe,
	// so allow attenuation only.
	if (truePeakDb === null || !Number.isFinite(truePeakDb)) return Math.min(wanted, 0);

	return Math.min(wanted, PEAK_CEILING_DBTP - truePeakDb);
}

export function dbToLinear(db: number): number {
	return 10 ** (db / 20);
}

/** Linear gain for the audio graph: normalization scaled by master volume. */
export function playbackGain(
	loudnessLufs: number | null,
	truePeakDb: number | null,
	volume: number
): number {
	const safeVolume = Number.isFinite(volume) ? Math.min(Math.max(volume, 0), 1) : 1;
	return dbToLinear(normalizationGainDb(loudnessLufs, truePeakDb)) * safeVolume;
}
