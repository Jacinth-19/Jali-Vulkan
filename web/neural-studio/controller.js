import {PRESETS,performanceSettings,summarizeObservation} from './settings.mjs';
import {ARTICULATION,articulation} from '../neural-head/articulation.mjs';
import {validateStreamChunk,AudioPrefetch} from './streaming.mjs';
/* Local CPU neural sessions. All browser requests are relative/same-origin. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let config = null, busy = false, phase = 'loading', verified = false, selectedId = null;
  const sessions = new Map();
  let currentJob=null, cancelPending=false, streaming=false;
  let streamStats=null,nativeFrame=null,nativeImageUrl=null,activePrefetch=null,nativeEpoch=0;
  let quality=performanceSettings(),calibration=articulation('clear');
  const nativeInfo={frames:0,lastTime:null,lastSession:null,lastMs:null,errors:[]};
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const error = message => { $('error').textContent = message; $('error').hidden = !message; };
  const update = () => {
    $('generate').disabled = $('text').value.length>($('batch').checked?1000:500) || busy || !config || !window.JaliHeadDemo?.getState().ready;
    $('text-count').textContent = `${$('text').value.length} / ${$('batch').checked?1000:500}`;
    $('text').disabled = busy;
    $('cancel').disabled = !busy || !currentJob || cancelPending;
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
  function validateClip(clip,expectedId){
    if (clip.id !== expectedId || !/^[a-f0-9]{32}$/.test(clip.id) || clip.file !== `/sessions/${clip.id}/audio.wav`
        || JSON.stringify(clip.rig) !== JSON.stringify(config.rig)
        || clip.analysis.audio_sha256 !== clip.audio.sha256) throw new Error('Session identity or audio/cue binding mismatch');
  }
  function disposePrepared(value,revoke=true){
    if(!value)return;value.preloader?.pause();value.preloader?.removeAttribute('src');value.preloader?.load();
    if(revoke)URL.revokeObjectURL(value.url);
  }
  async function prepareAudio(item,signal){
    const clip=item.clip;validateClip(clip,item.id);
    if(!crypto.subtle)throw new Error('Audio verification needs HTTPS or localhost');
    const response=await fetch(clip.file,{cache:'no-store',signal});if(!response.ok)throw new Error('Recording download failed');
    const bytes=await response.arrayBuffer();
    const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
    if(hash!==clip.audio.sha256)throw new Error('Downloaded audio differs from analyzed recording');
    if(signal?.aborted)throw new DOMException('Cancelled','AbortError');
    const value={url:URL.createObjectURL(new Blob([bytes],{type:'audio/wav'})),preloader:new Audio(),id:clip.id};
    try{
      await new Promise((resolve,reject)=>{
        const audio=value.preloader,timer=setTimeout(()=>done(new Error('Prebuffer decode timed out')),15000);
        function done(error){clearTimeout(timer);audio.oncanplay=audio.onerror=null;signal?.removeEventListener('abort',aborted);error?reject(error):resolve();}
        function aborted(){done(new DOMException('Cancelled','AbortError'));}
        audio.oncanplay=()=>done();audio.onerror=()=>done(new Error('Sentence audio decode failed'));signal?.addEventListener('abort',aborted,{once:true});
        audio.preload='auto';audio.src=value.url;audio.load();
      });
      if(Math.abs(value.preloader.duration-clip.duration)>.025)throw new Error('Decoded audio duration differs from cues');
      return value;
    }catch(error){disposePrepared(value);throw error;}
  }
  async function load(clip, expectedId, {autoplay=true,keepHistory=true,prepared=null}={}) {
    validateClip(clip,expectedId);
    prepared=prepared||await prepareAudio({clip,id:expectedId});
    if(streaming&&cancelPending){disposePrepared(prepared);return false;}
    if(prepared.id!==expectedId){disposePrepared(prepared);throw new Error('Wrong prebuffer identity');}
    const url=prepared.url;disposePrepared(prepared,false);
    try {
      JaliHeadDemo.loadSession({...clip,file:url},!keepHistory);
      const audio = $('audio');
      if (audio.readyState < 1) await new Promise((resolve,reject) => {
        const timeout = setTimeout(()=>{cleanup();reject(new Error('Audio metadata load timed out'));},15000);
        function cleanup(){clearTimeout(timeout);audio.removeEventListener('loadedmetadata',done);audio.removeEventListener('error',bad);}
        function done(){cleanup();resolve();} function bad(){cleanup();reject(new Error('Audio decode failed'));}
        audio.addEventListener('loadedmetadata',done); audio.addEventListener('error',bad);
      });
      if (Math.abs(audio.duration-clip.duration)>0.025) throw new Error('Decoded audio duration differs from cue timeline');
      if(streaming&&cancelPending){URL.revokeObjectURL(url);JaliHeadDemo.resetPerformance(true);return false;}
      if(keepHistory)history(clip);selectDetails(clip);if(!keepHistory)$('downloads').hidden=true;
      if(autoplay)await play();return true;
    } catch (failure) {URL.revokeObjectURL(url);JaliHeadDemo.resetPerformance();throw failure;}
  }
  async function followStream(id){
    const pool=new AudioPrefetch(prepareAudio,disposePrepared);activePrefetch=pool;
    let next=0,sample=0,lastEnded=null;
    function ahead(state,index,start){
      if(!$('prebuffer').checked||!Array.isArray(state.chunks))return;
      const item=state.chunks.find(c=>c.index===index);
      if(item){validateStreamChunk(item,index,start,state.sample_rate);if(!pool.entries.has(item.index))streamStats.downloadedAhead++;pool.add(item);}
    }
    try{const deadline=performance.now()+600000;
    streamStats={mode:'sentence-batched',firstPlayableMs:null,gapsMs:[],chunks:[],bufferingCount:0,prebufferHits:0,downloadedAhead:0};
    const began=performance.now();
    while(true){
      if(performance.now()>deadline)throw new Error('Sentence-batched playback deadline exceeded');
      const state=await json(`/api/jobs/${id}`);
      if(state.state==='cancelled'){JaliHeadDemo.resetPerformance(true);stage('cancelled','Sentence batching cancelled; queued audio and face data discarded.');return;}
      if(state.state==='error')throw new Error(state.error);
      if(state.state==='cancelling'){await sleep(150);continue;}
      if(state.state==='ready'){
        if(!await load(state.clip,id,{autoplay:false}))return;
        stage('ready','Sentence batches finished. The sample-concatenated recording is verified and ready to replay.');return;
      }
      if(!Array.isArray(state.chunks)||state.chunks.length>2||!Number.isInteger(state.chunk_count)||state.chunk_count>12)throw new Error('Invalid batch queue budget');
      const item=state.chunks.find(c=>c.index===next);
      if(!item){stage('buffering',`Buffering sentence batch ${next+1} of ${state.chunk_count}; face rests while audio is unavailable.`);streamStats.bufferingCount++;await sleep(250);continue;}
      const end=validateStreamChunk(item,next,sample,state.sample_rate);
      pool.add(item);ahead(state,next+1,end);
      const prepared=await pool.take(item);streamStats.prebufferHits=pool.hits;
      if(!await load({...item.clip,title:`Sentence batch ${next+1} / ${state.chunk_count}`,_stream_start_sample:item.start_sample},item.id,{keepHistory:false,prepared})){await sleep(150);continue;}
      if(streamStats.firstPlayableMs===null)streamStats.firstPlayableMs=performance.now()-began;
      if(lastEnded!==null)streamStats.gapsMs.push(performance.now()-lastEnded);
      streamStats.chunks.push({index:next,start_sample:sample,end_sample:end,audio_sha256:item.clip.audio.sha256});
      stage('playing-batch',`Playing verified sentence batch ${next+1} of ${state.chunk_count}. Later batches are bounded to two pending chunks.`);
      let checked=0,endedAt=null;
      const onEnded=()=>{endedAt=performance.now();};$('audio').addEventListener('ended',onEnded,{once:true});
      while(!$('audio').ended&&!cancelPending){
        if(performance.now()>deadline)throw new Error('Sentence playback timed out');
        if(performance.now()-checked>200){const status=await json(`/api/jobs/${id}`);if(status.state==='error')throw new Error(status.error);ahead(status,next+1,end);if(status.state==='cancelled'){cancelPending=true;break;}checked=performance.now();}
        await sleep(25);
      }
      $('audio').removeEventListener('ended',onEnded);
      if(cancelPending)continue;
      lastEnded=endedAt??performance.now();selectedId=null;await json('/api/ack',{method:'POST',headers:{'Content-Type':'application/json','X-Jali-Token':config.token},body:JSON.stringify({id,index:next})});
      sample=end;next++;
    }
    }finally{pool.close();if(activePrefetch===pool)activePrefetch=null;}
  }
  async function requestCancel(){
    if(!currentJob||cancelPending)return;cancelPending=true;activePrefetch?.close();if(streaming){selectedId=null;JaliHeadDemo.resetPerformance(true);}update();
    const cancelId=currentJob;
    try{await json('/api/cancel',{method:'POST',headers:{'Content-Type':'application/json','X-Jali-Token':config.token},body:JSON.stringify({id:currentJob})});if(currentJob===cancelId)stage('cancelling','Stopping generation and removing partial output…');}
    catch(failure){cancelPending=false;update();error(failure.message);}
  }
  $('renderer').addEventListener('change',()=>{
    nativeEpoch++;const native=$('renderer').value==='native';JaliHeadDemo.setNativeMode(native);$('native-face').hidden=!native;if(!native&&nativeImageUrl){URL.revokeObjectURL(nativeImageUrl);nativeImageUrl=null;$('native-face').removeAttribute('src');}
    $('renderer-label').textContent=native?'MPFB · CC0 · NATIVE VULKAN':'MPFB · CC0 · WEBGL';
    $('camera-label').textContent=native?'FIXED NATIVE PORTRAIT CAMERA':'DRAG TO ORBIT · SCROLL TO ZOOM';nativeFrame=null;
  });
  async function nativeTick(){
    const tickBegan=performance.now();
    try{
      if(config?.native&&$('renderer').value==='native'){
        const epoch=nativeEpoch,id=selectedId||'neutral',time=selectedId?($('audio').currentTime||0):0;
        const query=new URLSearchParams({id,time:String(time),trim:$('trim').value,mood:$('mood').value,gaze:$('gaze').value,life:$('life').checked?'1':'0',sync:$('sync').checked?'1':'0',resolution:String(quality.resolution),articulation:JSON.stringify(calibration)}),key=query.toString();
        if(nativeFrame!==key){
          const began=performance.now(),response=await fetch('/api/native/frame?'+query,{headers:{'X-Jali-Token':config.token},cache:'no-store'});
          if(epoch===nativeEpoch&&response.status!==409&&$('renderer').value==='native'&&id===(selectedId||'neutral')){
            if(!response.ok)throw new Error((await response.json()).error||'Native rendering failed');
            const blob=await response.blob();
            if(epoch===nativeEpoch&&$('renderer').value==='native'&&id===(selectedId||'neutral')){
              const url=URL.createObjectURL(blob),old=nativeImageUrl;nativeImageUrl=url;$('native-face').src=url;if(old)URL.revokeObjectURL(old);
              nativeFrame=key;nativeInfo.frames++;nativeInfo.lastTime=time;nativeInfo.lastSession=id;nativeInfo.lastMs=Number(response.headers.get('X-Jali-Render-Ms'));
              JaliHeadDemo.updateClock(time);if(window.JALI_RENDER_DIAGNOSTICS)window.dispatchEvent(new CustomEvent('jali-native-observation',{detail:{wallTime:performance.now(),renderMs:performance.now()-began,playing:!$('audio').paused}}));$('fps').textContent=`${(performance.now()-began).toFixed(0)} ms native response`;
            }
          }
        }
      }
    }catch(failure){nativeInfo.errors.push(failure.message);if(nativeInfo.errors.length>6)nativeInfo.errors.shift();error(failure.message);await sleep(1000);}
    setTimeout(nativeTick,Math.max(0,1000/quality.fps-(performance.now()-tickBegan)));
  }
  function saveSettings(){try{localStorage.setItem('jali.settings.'+JALI_HEAD_DATA.rig.model_sha256,JSON.stringify({quality,calibration}));}catch{}}
  function syncControls(){$('quality-preset').value=Object.keys(PRESETS).find(k=>JSON.stringify(PRESETS[k])===JSON.stringify(quality))||'custom';$('art-profile').value=Object.keys(ARTICULATION).find(k=>JSON.stringify(ARTICULATION[k])===JSON.stringify(calibration))||'custom';for(const k of ['fps','resolution','pixelRatio'])$('quality-'+k).value=String(quality[k]);for(const k of Object.keys(ARTICULATION.baseline))if(k!=='smooth'){$('art-'+k).value=calibration[k];$('art-'+k+'-value').textContent=calibration[k];}}
  function applySettings(){nativeEpoch++;quality=performanceSettings(quality);calibration=articulation(calibration);JaliHeadDemo.setPerformance(quality);JaliHeadDemo.setArticulation(calibration);nativeFrame=null;syncControls();saveSettings();}
  try{const saved=JSON.parse(localStorage.getItem('jali.settings.'+JALI_HEAD_DATA.rig.model_sha256));if(saved){quality=performanceSettings(saved.quality);calibration=articulation(saved.calibration);}}catch{}
  const requested=new URLSearchParams(location.search).get('preset');if(PRESETS[requested])quality=performanceSettings(requested);
  $('quality-preset').addEventListener('change',()=>{quality=performanceSettings($('quality-preset').value);applySettings();});
  for(const key of ['fps','resolution','pixelRatio'])$('quality-'+key).addEventListener('change',()=>{quality={...quality,[key]:Number($('quality-'+key).value)};applySettings();});
  $('art-profile').addEventListener('change',()=>{calibration=articulation($('art-profile').value);applySettings();});
  for(const key of Object.keys(ARTICULATION.baseline).filter(k=>k!=='smooth'))$('art-'+key).addEventListener('input',()=>{calibration={...calibration,[key]:Number($('art-'+key).value)};applySettings();});
  $('observe').addEventListener('click',async()=>{
    if($('audio').paused){error('Play a recording first, then observe it.');return;}
    const frames=[],settings={...quality},observedEpoch=nativeEpoch;$('observe').disabled=true;const began=performance.now();
    const capture=e=>{if(e.type==='jali-render'&&$('renderer').value==='native')return;if(e.detail.playing)frames.push({time:e.detail.wallTime,cost:e.detail.renderMs});};
    window.JALI_RENDER_DIAGNOSTICS=true;window.addEventListener('jali-render',capture);window.addEventListener('jali-native-observation',capture);
    await sleep(10000);window.removeEventListener('jali-render',capture);window.removeEventListener('jali-native-observation',capture);window.JALI_RENDER_DIAGNOSTICS=false;$('observe').disabled=false;
    try{if(observedEpoch!==nativeEpoch||JSON.stringify(settings)!==JSON.stringify(quality))throw Error('Settings or renderer changed during observation; repeat it');const report=summarizeObservation(frames,settings);report.renderer=$('renderer').value;report.calibration=calibration;report.elapsed_ms=performance.now()-began;$('apply-recommendation').hidden=!report.recommended_preset;$('apply-recommendation').onclick=()=>{quality=performanceSettings(report.recommended_preset);applySettings();};$('observation').textContent=JSON.stringify(report,null,2);const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const old=$('observation-download').href;if(old.startsWith('blob:'))URL.revokeObjectURL(old);$('observation-download').href=url;$('observation-download').hidden=false;}catch(failure){error(failure.message);}
  });
  window.addEventListener('jali-head-ready',applySettings);applySettings();
  nativeTick();
  $('compose').addEventListener('submit', async event => {
    event.preventDefault(); if (busy || !config || !JaliHeadDemo.getState().ready) return;
    currentJob=null;cancelPending=false;streaming=$('batch').checked;streamStats=null;
    busy = true; verified = false; selectedId = null; error('');
    $('verified').textContent = 'PREPARING NEW RECORDING'; $('metrics').textContent = '';
    $('downloads').hidden = true; $('resume').hidden = true;
    JaliHeadDemo.resetPerformance(); update(); stage('synthesizing','Generating a new neural recording locally on CPU…');
    try {
      const job = await json(streaming?'/api/stream':'/api/generate',{method:'POST',headers:{'Content-Type':'application/json','X-Jali-Token':config.token},body:JSON.stringify({text:$('text').value})});
      currentJob=job.id;update();
      if(streaming){await followStream(job.id);return;}
      const deadline = performance.now()+210000;
      while (true) {
        if (performance.now()>deadline) throw new Error('Local job timed out. Refresh to check the server.');
        const state = await json(`/api/jobs/${job.id}`);
        if (state.state === 'cancelled') {JaliHeadDemo.resetPerformance(true);stage('cancelled','Cancelled. Partial output was discarded; you can generate again.');break;}
        if (state.state === 'cancelling') stage('cancelling','Stopping the owned speech/analyzer process…');
        if (state.state === 'error') throw new Error(state.error);
        if (state.state === 'ready') {stage('ready','Verifying the recording and loading its matching mouth cues…'); await load(state.clip,job.id);break;}
        if (state.stage === 'analyzing') stage('analyzing','Analyzing this exact WAV with its script. No reused speech timings…');
        await sleep(700);
      }
    } catch (failure) {if(cancelPending){
      JaliHeadDemo.resetPerformance(true);
      // An aborted prefetch can reject before the owned producer has exited.
      // Keep retry disabled until cleanup is confirmed, rather than racing 409.
      const deadline=performance.now()+30000;
      while(currentJob){const state=await json(`/api/jobs/${currentJob}`);if(['cancelled','ready','error'].includes(state.state))break;if(performance.now()>deadline)throw Error('Cancellation cleanup timed out; check the server before retrying');await sleep(100);}
      stage('cancelled','Cancelled. Queued audio was discarded.');return;
    }if(streaming&&currentJob&&!cancelPending)await requestCancel();JaliHeadDemo.resetPerformance(true);stage('error','Generation did not complete. No fallback performance was substituted.');error(failure.message);}
    finally {busy=false;currentJob=null;cancelPending=false;streaming=false;update();}
  });
  $('cancel').addEventListener('click',requestCancel);
  $('stop').addEventListener('click',()=>{if(busy&&streaming)requestCancel();JaliHeadDemo.resetPerformance(true);selectedId=null;verified=false;$('downloads').hidden=true;$('resume').hidden=true;$('verified').textContent='PLAYBACK STOPPED';if(!busy)stage('idle','Stopped. Choose history to replay or generate new words.');});
  $('resume').addEventListener('click',()=>play().catch(failure=>error(failure.message)));
  $('text').addEventListener('input',update);
  $('batch').addEventListener('change',()=>{$('text').maxLength=$('batch').checked?1000:500;update();});
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
  window.JaliStudio = {loadExisting:async id=>{
    if(busy||!/^[a-f0-9]{32}$/.test(id))throw new Error('Invalid/busy existing-session request');
    const value=await json('/api/jobs/'+id);if(value.state!=='ready')throw new Error('Existing session is not ready');
    await load(value.clip,id,{autoplay:false});$('resume').hidden=false;stage('ready','Existing recording verified and loaded.');update();
  },getState:()=>({quality,calibration,busy,phase,verified,selectedId,currentJob,cancelPending,streaming,streamStats,nativeInfo})};
  json('/api/config').then(value=>{
    if (JSON.stringify(value.rig)!==JSON.stringify(JALI_HEAD_DATA.rig)) throw new Error('Viewer and backend rig versions differ; rebuild the studio.');
    config=value; if(config.native){$('native-option').disabled=false;$('native-option').textContent='Native Vulkan — '+config.native.device;}
    if(new URLSearchParams(location.search).get('renderer')==='native'&&config.native){$('renderer').value='native';$('renderer').dispatchEvent(new Event('change'));}
    if (JaliHeadDemo.getState().ready) stage('idle','Ready. Write a sentence, then generate your performance.');update();
  }).catch(failure=>{error(failure.message);stage('error','The local generation service is unavailable.');});
  update();
})();
