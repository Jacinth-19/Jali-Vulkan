/* Local CPU neural sessions. All browser requests are relative/same-origin. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let config = null, busy = false, phase = 'loading', verified = false, selectedId = null;
  const sessions = new Map();
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const error = message => { $('error').textContent = message; $('error').hidden = !message; };
  const update = () => {
    $('generate').disabled = busy || !config || !window.JaliHeadDemo?.getState().ready;
    $('text-count').textContent = `${$('text').value.length} / 500`;
    $('text').disabled = busy;
    document.querySelectorAll('#history button').forEach(button => {button.disabled = busy;});
  };
  function stage(value, message) {
    phase = value; $('status').textContent = message;
    const order = ['synthesizing','analyzing','ready'];
    ['voice','cues','play'].forEach((name,index) => {
      const node = $('step-'+name); node.className = '';
      if (order.indexOf(value) === index) node.className = 'active';
      if (order.indexOf(value) > index) node.className = 'done';
    });
  }
  async function json(url, options) {
    const response = await fetch(url, {...options, cache:'no-store'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Local request failed (${response.status})`);
    return data;
  }
  function selectDetails(clip) {
    selectedId = clip.id; verified = true;
    $('verified').textContent = 'WAV HASH VERIFIED';
    $('session-info').textContent = `Session ${clip.id}\nSHA-256 ${clip.audio.sha256}`;
    $('metrics').textContent = `${clip.duration.toFixed(2)} s audio · ${clip.generation_seconds.toFixed(2)} s synthesis · ${clip.analysis_seconds.toFixed(2)} s analysis\n${clip.tts.process_peak_rss_mib ?? 'unmeasured'} MiB worker peak · CPU only`;
    $('downloads').hidden = false;
    $('download-audio').href = `/sessions/${clip.id}/audio.wav`;
    $('download-cues').href = `/sessions/${clip.id}/cues.json`;
    $('download-manifest').href = `/sessions/${clip.id}/manifest.json`;
    for (const button of $('history').querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.session === clip.id));
  }
  async function play() {
    try {
      await $('audio').play(); $('resume').hidden = true;
      stage('ready','Playing the new recording with its own mouth cues. Pause or seek below.');
    } catch (failure) {
      if (failure.name !== 'NotAllowedError') throw failure;
      $('resume').hidden = false;
      stage('ready','Ready. Your browser requires a Play click after generation.');
    }
  }
  function history(clip) {
    if (!sessions.size) $('history').replaceChildren();
    sessions.set(clip.id, clip);
    const button = document.createElement('button'); button.type = 'button'; button.dataset.session = clip.id;
    const label = document.createElement('span'); label.textContent = clip.text.slice(0,80)+(clip.text.length>80?'…':'');
    const detail = document.createElement('small'); detail.textContent = `${clip.duration.toFixed(2)} s · ${clip.id.slice(0,8)} · actual-WAV cues`;
    button.append(label,detail);
    button.addEventListener('click', async () => {
      if (busy) return;
      try {
        const index = JaliHeadDemo.getState().clips.findIndex(c => c.id === clip.id);
        JaliHeadDemo.selectClip(index); await play();
      } catch (failure) {error(failure.message);}
    });
    $('history').prepend(button);
    if (sessions.size > 6) {
      const old = sessions.keys().next().value; sessions.delete(old);
      $('history').querySelector(`[data-session="${old}"]`)?.remove();
    }
  }
  async function load(clip, expectedId) {
    if (clip.id !== expectedId || !/^[a-f0-9]{32}$/.test(clip.id) || clip.file !== `/sessions/${clip.id}/audio.wav`
        || JSON.stringify(clip.rig) !== JSON.stringify(config.rig)
        || clip.analysis.audio_sha256 !== clip.audio.sha256) throw new Error('Session identity or audio/cue binding mismatch');
    if (!crypto.subtle) throw new Error('Audio verification needs HTTPS or localhost. Open the secure preview.');
    const response = await fetch(clip.file, {cache:'no-store'});
    if (!response.ok) throw new Error('New recording could not be downloaded');
    const bytes = await response.arrayBuffer();
    const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)), b=>b.toString(16).padStart(2,'0')).join('');
    if (digest !== clip.audio.sha256) throw new Error('Downloaded audio differs from the analyzed recording');
    const url = URL.createObjectURL(new Blob([bytes], {type:'audio/wav'}));
    try {
      JaliHeadDemo.loadSession({...clip,file:url});
      const audio = $('audio');
      if (audio.readyState < 1) await new Promise((resolve,reject) => {
        const timeout = setTimeout(()=>{cleanup();reject(new Error('Audio metadata load timed out'));},15000);
        function cleanup(){clearTimeout(timeout);audio.removeEventListener('loadedmetadata',done);audio.removeEventListener('error',bad);}
        function done(){cleanup();resolve();} function bad(){cleanup();reject(new Error('Audio decode failed'));}
        audio.addEventListener('loadedmetadata',done); audio.addEventListener('error',bad);
      });
      if (Math.abs(audio.duration-clip.duration)>0.025) throw new Error('Decoded audio duration differs from cue timeline');
      history(clip); selectDetails(clip); await play();
    } catch (failure) {URL.revokeObjectURL(url);JaliHeadDemo.resetPerformance();throw failure;}
  }
  $('compose').addEventListener('submit', async event => {
    event.preventDefault(); if (busy || !config || !JaliHeadDemo.getState().ready) return;
    busy = true; verified = false; selectedId = null; error('');
    $('verified').textContent = 'PREPARING NEW RECORDING'; $('metrics').textContent = '';
    $('downloads').hidden = true; $('resume').hidden = true;
    JaliHeadDemo.resetPerformance(); update(); stage('synthesizing','Generating a new neural recording locally on CPU…');
    try {
      const job = await json('/api/generate',{method:'POST',headers:{'Content-Type':'application/json','X-Jali-Token':config.token},body:JSON.stringify({text:$('text').value})});
      const deadline = performance.now()+210000;
      while (true) {
        if (performance.now()>deadline) throw new Error('Local job timed out. Refresh to check the server.');
        const state = await json(`/api/jobs/${job.id}`);
        if (state.state === 'error') throw new Error(state.error);
        if (state.state === 'ready') {stage('ready','Verifying the recording and loading its matching mouth cues…'); await load(state.clip,job.id);break;}
        if (state.stage === 'analyzing') stage('analyzing','Analyzing this exact WAV with its script. No reused speech timings…');
        await sleep(700);
      }
    } catch (failure) {stage('error','Generation did not complete. No fallback performance was substituted.');error(failure.message);}
    finally {busy=false;update();}
  });
  $('resume').addEventListener('click',()=>play().catch(failure=>error(failure.message)));
  $('text').addEventListener('input',update);
  $('audio').addEventListener('pause',()=>{
    if (!busy && selectedId) $('status').textContent = 'Paused. Seek the recording or press Play to continue.';
  });
  $('audio').addEventListener('ended',()=>{
    if (!busy && selectedId) $('status').textContent = 'Finished. Replay this session or generate new words.';
  });
  $('audio').addEventListener('play',()=>{
    if (!busy && selectedId) $('status').textContent = 'Playing this recording with its own mouth cues.';
  });
  window.addEventListener('jali-head-ready',()=>{
    if (config) stage('idle','Ready. Write a sentence, then generate your performance.');update();
  });
  window.addEventListener('jali-clip-selected',event=>{
    const clip = sessions.get(event.detail.id); if (clip) selectDetails(clip);
  });
  window.JaliStudio = {getState:()=>({busy,phase,verified,selectedId})};
  json('/api/config').then(value=>{
    if (JSON.stringify(value.rig)!==JSON.stringify(JALI_HEAD_DATA.rig)) throw new Error('Viewer and backend rig versions differ; rebuild the studio.');
    config=value; if (JaliHeadDemo.getState().ready) stage('idle','Ready. Write a sentence, then generate your performance.');update();
  }).catch(failure=>{error(failure.message);stage('error','The local generation service is unavailable.');});
  update();
})();
