'use strict';
const $ = id => document.getElementById(id);
const canvas = $('canvas'), pixels = canvas.getContext('2d', { alpha: false });
const text = $('text');
let context, gain, source, buffer, session, cues = [];
let busy = false, playing = false, edited = false, offset = 0, startTime = 0;
let audioEpoch = 0, sessionEpoch = 0, frameTask = null, previewNeeded = false, seeking = false;
let framesReceived = 0, rtt = 0.02, latestOffset = 0;
const bytes = value => new TextEncoder().encode(value).length;
const clock = value => `${String(Math.floor((value || 0) / 60)).padStart(2, '0')}:${String(Math.floor((value || 0) % 60)).padStart(2, '0')}`;
function error(message) { $('error').textContent = message || ''; $('error').hidden = !message; }
function updateCount() {
  const count = bytes(text.value);
  $('charCount').textContent = `${count} / 240 bytes`;
  $('charCount').style.color = count > 240 ? '#f6a1ad' : '';
  $('generate').disabled = busy || !text.value.trim() || count > 240;
}
function metric(id, value, unit = '') {
  const children = [document.createTextNode(String(value))];
  if (unit) { const small = document.createElement('small'); small.textContent = unit; children.push(small); }
  $(id).replaceChildren(...children);
}
function audioContext() {
  if (!context) {
    const Audio = window.AudioContext || window.webkitAudioContext;
    if (!Audio) throw new Error('This browser does not support Web Audio.');
    context = new Audio(); gain = context.createGain(); gain.connect(context.destination);
  }
  return context;
}
function cursor() {
  if (!playing) return offset;
  let now = context.currentTime;
  const stamp = context.getOutputTimestamp?.();
  if (stamp?.performanceTime > 0 && stamp.contextTime > 0) {
    now = stamp.contextTime + (performance.now() - stamp.performanceTime) / 1000;
  } else now -= (context.baseLatency || 0) + (context.outputLatency || 0);
  return Math.min(buffer.duration, Math.max(0, offset + now - startTime));
}
function pause() {
  if (!playing) return;
  offset = cursor(); playing = false; audioEpoch++;
  if (source) { source.onended = null; source.stop(); source.disconnect(); source = null; }
  previewNeeded = true;
}
async function play() {
  if (!buffer || busy) return;
  try {
    await audioContext().resume();
    if (offset >= buffer.duration - 0.001) offset = 0;
    const epoch = ++audioEpoch;
    source = context.createBufferSource(); source.buffer = buffer; source.connect(gain);
    startTime = context.currentTime + 0.06;
    playing = true;
    source.onended = () => { if (epoch === audioEpoch) { playing = false; offset = buffer.duration; previewNeeded = true; } };
    source.start(startTime, offset);
  } catch (failure) { error(`Audio playback failed: ${failure.message}`); }
}
function setBusy(value) {
  busy = value; $('renderOverlay').hidden = !value;
  $('generateLabel').textContent = value ? 'Preparing live session…' : 'Start live performance';
  text.disabled = value;
  document.querySelectorAll('[data-prompt]').forEach(button => button.disabled = value);
  updateCount();
}
async function jsonRequest(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
async function loadSession(meta, autoplay = false) {
  pause(); sessionEpoch++;
  if (frameTask) await frameTask;
  const ctx = audioContext();
  const audioResponse = await fetch(meta.audio_url);
  if (!audioResponse.ok) throw new Error('Could not load the synthesized PCM audio.');
  buffer = await ctx.decodeAudioData(await audioResponse.arrayBuffer());
  cues = await (await fetch(meta.cues_url)).json();
  session = meta; offset = 0; framesReceived = 0; latestOffset = 0;
  canvas.dataset.durationSeconds = String(buffer.duration);
  canvas.dataset.sessionId = meta.id;
  canvas.width = meta.width; canvas.height = meta.height;
  $('download').href = meta.audio_url;
  $('device').textContent = `${meta.device} · ${meta.hardware_accelerated ? 'hardware' : 'software'}`;
  $('deviceBadge').textContent = meta.hardware_accelerated ? 'HARDWARE VULKAN' : 'SOFTWARE VULKAN';
  $('resolutionHud').textContent = `${meta.width} × ${meta.height} / LIVE SKINNING`;
  $('rigInfo').textContent = `${meta.vertices.toLocaleString()} vertices · ${meta.bones} joints · ${meta.morph_targets} morph targets`;
  metric('duration', buffer.duration.toFixed(2), 's'); metric('frames', 0);
  metric('lag', '—', 'ms'); metric('generation', meta.prepare_seconds.toFixed(2), 's');
  $('sessionState').textContent = 'Live renderer ready · phoneme-aligned';
  if (meta.text && (!edited || autoplay)) text.value = meta.text;
  previewNeeded = true; updateCount();
  if (autoplay) await play();
}
async function requestFrame() {
  const epoch = sessionEpoch;
  // Resampling and decimal serialization must never request beyond native PCM duration.
  const last = Math.max(0, Math.min(buffer.duration, session.duration_seconds) - 0.000001);
  const time = Math.floor(Math.min(last, cursor() + (playing ? Math.min(0.1, rtt * 0.5) : 0)) * 1e6) / 1e6;
  previewNeeded = false;
  const started = performance.now();
  try {
    const response = await fetch(`/api/live/frame?id=${encodeURIComponent(session.id)}&time=${time.toFixed(6)}`, { cache: 'no-store' });
    if (!response.ok) {
      if (response.status === 409) { previewNeeded = true; return; }
      const data = await response.json(); throw new Error(data.error || 'Native render request failed');
    }
    const image = await createImageBitmap(await response.blob());
    if (epoch === sessionEpoch) {
      pixels.drawImage(image, 0, 0, canvas.width, canvas.height);
      canvas.dataset.frameSeconds = response.headers.get('X-Audio-Time');
      framesReceived++; rtt = rtt * 0.75 + (performance.now() - started) / 1000 * 0.25;
      latestOffset = (cursor() - Number(response.headers.get('X-Audio-Time'))) * 1000;
      metric('frames', framesReceived); metric('lag', Math.round(latestOffset).toFixed(0), 'ms');
      $('lag').style.color = Math.abs(latestOffset) > 100 ? '#f6a1ad' : '';
      let cue = '';
      for (const c of cues) { if (c.seconds > time) break; cue = c.symbol; }
      $('phonemeHud').textContent = cue.startsWith('_') ? 'REST' : `PHONEME / ${cue || 'REST'}`;
      $('sessionState').textContent = `${playing ? 'Playing live' : 'Live renderer ready'} · ${Number(response.headers.get('X-Render-Ms')).toFixed(1)} ms frame service`;
    }
    image.close();
  } catch (failure) {
    if (epoch === sessionEpoch) { pause(); previewNeeded = false; error(failure.message); }
  }
}
function tick() {
  const position = cursor(), duration = buffer?.duration || 0;
  canvas.dataset.audioSeconds = position.toFixed(6);
  canvas.dataset.playing = String(playing);
  $('timecode').textContent = `${clock(position)} / ${clock(duration)}`;
  if (!seeking) $('seek').value = duration > 0 ? position / duration * 1000 : 0;
  $('playOverlay').hidden = playing;
  $('playButton').setAttribute('aria-label', playing ? 'Pause' : 'Play');
  $('transportIcon').firstElementChild.setAttribute('d', playing ? 'M6 5h4v14H6zM14 5h4v14h-4z' : 'M8 5v14l11-7z');
  if (session && buffer && !busy && !frameTask && (playing || previewNeeded)) {
    frameTask = requestFrame().finally(() => { frameTask = null; });
  }
  requestAnimationFrame(tick);
}
async function togglePlay() { if (!session || busy) return; if (playing) pause(); else await play(); }
$('playButton').addEventListener('click', togglePlay); $('playOverlay').addEventListener('click', togglePlay);
canvas.addEventListener('click', togglePlay);
$('seek').addEventListener('input', () => {
  if (!buffer || busy) return;
  const wasPlaying = playing; pause(); seeking = true;
  offset = Number($('seek').value) / 1000 * buffer.duration; previewNeeded = true;
  if (wasPlaying) play();
});
$('seek').addEventListener('change', () => { seeking = false; });
$('muteButton').addEventListener('click', () => {
  audioContext(); gain.gain.value = gain.gain.value ? 0 : 1;
  $('muteButton').textContent = gain.gain.value ? 'SOUND ON' : 'SOUND OFF';
  $('muteButton').setAttribute('aria-label', gain.gain.value ? 'Mute audio' : 'Unmute audio');
});
$('fullButton').addEventListener('click', () => canvas.requestFullscreen?.().catch(() => {}));
text.addEventListener('input', () => { edited = true; updateCount(); });
document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => {
  text.value = button.dataset.prompt; edited = true; updateCount(); text.focus();
}));
$('speechForm').addEventListener('submit', async event => {
  event.preventDefault(); if (busy || bytes(text.value) > 240 || !text.value.trim()) return;
  error(''); pause(); setBusy(true);
  try {
    await audioContext().resume();
    if (frameTask) await frameTask;
    $('renderStage').textContent = 'Synthesizing phoneme cues and importing the skinned mesh';
    const result = await jsonRequest('/api/live/session', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: text.value }) });
    await loadSession(result.session, false);
    setBusy(false); await play();
  } catch (failure) { error(failure.message); } finally { setBusy(false); }
});
updateCount(); requestAnimationFrame(tick);
jsonRequest('/api/live/session').then(async data => {
  if (data.session) await loadSession(data.session);
  else $('sessionState').textContent = 'Enter text to prepare a live session';
}).catch(failure => { error(failure.message); $('sessionState').textContent = 'Live backend unavailable'; });
