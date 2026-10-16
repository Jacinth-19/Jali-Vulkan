// Render-completion observations: NOT GPU timer queries or physical AV latency.
export function summarizeFrames(frames) {
  if (!Array.isArray(frames)) throw new Error('Expected render observations');
  let previous = -Infinity;
  for (const frame of frames) {
    if (!Number.isFinite(frame.wallTime) || frame.wallTime <= previous ||
        !Number.isFinite(frame.audioTime) || frame.audioTime < 0 ||
        !Number.isFinite(frame.renderMs) || frame.renderMs < 0) throw new Error('Invalid render observation');
    previous = frame.wallTime;
  }
  const gaps = frames.slice(1).map((f,i)=>f.wallTime-frames[i].wallTime).sort((a,b)=>a-b);
  const costs = frames.map(f=>f.renderMs).sort((a,b)=>a-b);
  const percentile = (values,p) => values.length ? values[Math.ceil(values.length*p)-1] : null;
  const span = frames.length > 1 ? frames.at(-1).wallTime-frames[0].wallTime : 0;
  return {
    rendered_frames: frames.length, observed_span_seconds: span/1000,
    observed_render_fps: span > 0 ? (frames.length-1)*1000/span : null,
    median_frame_gap_ms:percentile(gaps,.5), p95_frame_gap_ms:percentile(gaps,.95),
    max_frame_gap_ms:gaps.at(-1)??null, p95_cpu_submission_ms:percentile(costs,.95),
    first_audio_time:frames[0]?.audioTime??null, last_audio_time:frames.at(-1)?.audioTime??null,
    method:'Visible-tab render-completion samples during actual audio playback; CPU submission time, not GPU execution or physical AV latency'
  };
}
