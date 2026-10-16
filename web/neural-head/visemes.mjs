import {articulation,calibrated} from './articulation.mjs';
// Rhubarb A–H/X are estimated mouth classes, not literal phoneme labels.
export const SHAPES = Object.freeze({
  X: { label: 'Rest / silence', weights: {} },
  A: { label: 'P / B / M', weights: { viseme_PP: 0.95 } },
  B: { label: 'Consonants / EE', weights: { viseme_I: 0.35, viseme_SS: 0.35 } },
  C: { label: 'EH / AE', weights: { viseme_E: 0.72, viseme_aa: 0.08 } },
  D: { label: 'Open AA', weights: { viseme_aa: 0.88 } },
  E: { label: 'Rounded AO / ER', weights: { viseme_O: 0.65, viseme_RR: 0.15 } },
  F: { label: 'Puckered OO / W', weights: { viseme_U: 0.88, viseme_O: 0.12 } },
  G: { label: 'F / V', weights: { viseme_FF: 0.85 } },
  H: { label: 'L / tongue up', weights: { viseme_nn: 0.65, viseme_DD: 0.22 } }
});

export function validateCues(cues, duration) {
  if (!Number.isFinite(duration) || duration <= 0 || duration > 60 || !Array.isArray(cues) || !cues.length || cues.length > 10000) throw new Error('Invalid mouth-cue timeline');
  let previous = 0;
  for (const cue of cues) {
    if (!Number.isFinite(cue.start) || !Number.isFinite(cue.end) || cue.start < 0 || cue.end <= cue.start || cue.end > duration + 0.025 || !Object.prototype.hasOwnProperty.call(SHAPES, cue.value) || Math.abs(cue.start - previous) > 0.025) throw new Error('Invalid, missing, or overlapping mouth cue');
    previous = cue.end;
  }
  if (Math.abs(previous - duration) > 0.025) throw new Error('Mouth cues do not cover the audio duration');
  return true;
}

export function sampleVisemes(cues, time, enabled = true, profile = 'baseline') {
  if (!Number.isFinite(time)) throw new Error('Invalid audio time');
  if (!enabled || !cues.length || time < cues[0].start || time >= cues[cues.length - 1].end) return { value: 'X', label: SHAPES.X.label, weights: {} };
  let low = 0, high = cues.length;
  while (low < high) {
    const mid = (low + high) >>> 1;
    if (cues[mid].start <= time) low = mid + 1; else high = mid;
  }
  const index = Math.max(0, low - 1), cue = cues[index];
  const calibration=articulation(profile);
  const shape = SHAPES[cue.value], next = cues[index + 1];
  const weights = calibrated(shape.weights,calibration);
  if (next) {
    // Preserve the first 65% even of a 10-20ms cue. A fixed 35ms
    // window used to blend an entire short lip closure away.
    const transition = Math.min(calibration.transition/1000, (cue.end - cue.start) * 0.35);
    const start = cue.end - transition;
    let alpha = transition===0?0:Math.max(0, Math.min(1, (time - start) / transition));
    if(calibration.smooth)alpha=alpha*alpha*(3-2*alpha);
    const other = calibrated(SHAPES[next.value].weights,calibration);
    if (alpha > 0) for (const key of new Set([...Object.keys(weights), ...Object.keys(other)])) weights[key] = (weights[key] || 0) * (1 - alpha) + (other[key] || 0) * alpha;
  }
  return { value: cue.value, label: shape.label, weights };
}

// The audio duration is authoritative: rounded cue ends and negative manual trim
// must never leave a speaking pose at the actual end of playback.
export function sampleClipVisemes(clip, time, offset = 0, enabled = true, profile = 'baseline') {
  if (!Number.isFinite(time) || !Number.isFinite(offset)) throw new Error('Invalid playback time or trim');
  if (clip && (!Number.isFinite(clip.duration) || clip.duration <= 0)) throw new Error('Invalid clip duration');
  if (!clip || time < 0 || time >= clip.duration) return { value:'X', label:SHAPES.X.label, weights:{} };
  return sampleVisemes(clip.cues, time + offset, enabled, profile);
}
