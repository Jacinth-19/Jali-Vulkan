import { summarizeFrames } from './measurement.mjs';
const $=id=>document.getElementById(id), data=window.JALI_HEAD_DATA, audio=$('audio');
const notes=data.clips.map(()=>({rating:'pending',notes:''})), runs=[];
let selected=0, active=null, timer=null, loaded=false;
const status=text=>$('measurement-status').textContent=text;
function storeNote(){notes[selected]={rating:$('rating').value,notes:$('notes').value};}
function finish(reason){
  if(!active)return;
  const captured=active;active=null;clearTimeout(timer);audio.pause();
  const result={clip_id:captured.clipId,completed:reason==='ended',reason,visibility_valid:captured.visible,
    settings:captured.settings,diagnostics:captured.diagnostics,...summarizeFrames(captured.frames)};
  result.valid_sample=result.completed&&result.visibility_valid&&result.rendered_frames>=2;
  runs.push(result);window.JALI_RENDER_DIAGNOSTICS=false;
  $('measure').disabled=false;$('cancel').disabled=true;
  $('raw-result').textContent=JSON.stringify(result,null,2);
  $('result').textContent=result.valid_sample
    ? `Observed render rate: ${result.observed_render_fps.toFixed(1)} fps\n95th-percentile frame gap: ${result.p95_frame_gap_ms.toFixed(1)} ms\n95th-percentile CPU submission: ${result.p95_cpu_submission_ms.toFixed(1)} ms\nFrames observed: ${result.rendered_frames} over ${result.observed_span_seconds.toFixed(2)} s\nNot GPU execution time or physical AV latency.`
    : `No usable performance sample (${reason}).\nRepeat the recording without interruption.`;
  status(result.valid_sample?'Measurement complete. This is browser playback only.':`Incomplete measurement: ${reason}. No performance conclusion.`);
}
function exportReport(){
  storeNote();
  return {schema:'jali-playback-checkpoint-v1',created_at:new Date().toISOString(),
    scope:'Offline browser playback of fixed synthetic clips; not local TTS, native Vulkan, hardware-GPU proof, or physical AV latency',
    independently_verified_phoneme_alignment:false,user_review_declared_complete:notes.every(n=>n.rating!=='pending'),human_review_independently_verified:false,quality_score:null,
    corpus:data.clips.map((c,i)=>({id:c.id,text:c.text,audio_sha256:c.audio.sha256,rig:c.rig,...notes[i]})),
    conditions:$('conditions').value,runs,
    browser:{user_agent:navigator.userAgent,platform:navigator.platform,hardware_concurrency_hint:navigator.hardwareConcurrency??null,
      device_memory_gib_hint:navigator.deviceMemory??null,viewport:{width:innerWidth,height:innerHeight},device_pixel_ratio:devicePixelRatio},
    privacy:'Created locally at your request. Contains notes and system/browser hints; inspect before sharing. No automatic upload.'};
}
for(const [index,clip] of data.clips.entries()){
  const button=document.createElement('button');button.textContent=clip.title;button.dataset.clip=String(index);button.disabled=true;
  button.addEventListener('click',()=>{finish('clip switched');storeNote();selected=index;JaliHeadDemo.selectClip(index);$('rating').value=notes[index].rating;$('notes').value=notes[index].notes;$('review-hint').textContent=clip.review;audio.playbackRate=Number($('speed').value);});
  $('clips').append(button);
}
$('review-hint').textContent=data.clips[0].review;
$('speed').addEventListener('change',()=>{finish('speed changed');audio.playbackRate=Number($('speed').value);});
for(const id of ['sync','life','mood','trim'])$(id).addEventListener('change',()=>finish('settings changed'));
$('trim').addEventListener('input',()=>finish('settings changed'));
window.addEventListener('jali-render',event=>{
  const f=event.detail;
  if(active?.phase==='playing'&&f.playing&&!f.seeking&&f.audioTime>0&&!document.hidden){
    if(!active.frames.length||f.wallTime>active.frames.at(-1).wallTime)active.frames.push({wallTime:f.wallTime,audioTime:f.audioTime,renderMs:f.renderMs});
  }
});
audio.addEventListener('ended',()=>{if(active?.phase==='playing')finish('ended');});
audio.addEventListener('pause',()=>{if(active?.phase==='playing'&&audio.paused&&!audio.ended)finish('playback paused');});
audio.addEventListener('seeking',()=>{if(active?.phase==='playing'&&active.frames.length)finish('seek during measurement');});
audio.addEventListener('ratechange',()=>{if(active&&audio.playbackRate!==1)finish('speed changed');});
audio.addEventListener('error',()=>finish('audio error'));
document.addEventListener('visibilitychange',()=>{if(active&&document.hidden){active.visible=false;finish('tab hidden');}});
$('face').addEventListener('webglcontextlost',()=>finish('WebGL context lost'));
window.addEventListener('resize',()=>finish('viewport resized'));
$('measure').addEventListener('click',async()=>{
  if(active||!loaded)return;
  audio.pause();audio.currentTime=0;audio.playbackRate=1;$('speed').value='1';
  $('sync').checked=true;$('life').checked=false;$('mood').value='neutral';$('trim').value='0';
  const captured=active={phase:'starting',clipId:data.clips[selected].id,frames:[],visible:!document.hidden,
    settings:{speed:1,speech_animation:true,procedural_motion:false,mood:'neutral',trim_ms:0,render_target_fps:30},diagnostics:JaliHeadDemo.getDiagnostics()};
  window.JALI_RENDER_DIAGNOSTICS=true;$('measure').disabled=true;$('cancel').disabled=false;status('Measuring actual playback. Keep this tab visible…');
  timer=setTimeout(()=>finish('timeout'),90000);
  // Pause/seek events queued by the reset must not invalidate the NEW run.
  // play() completion is owned by this capture; a late completion/rejection
  // after Cancel must never end or resume a later measurement.
  try{await audio.play();if(active===captured){captured.phase='playing';if(audio.ended)finish('ended');}}catch{if(active===captured)finish('audio playback blocked');}
});
$('cancel').addEventListener('click',()=>finish('cancelled'));
$('download').addEventListener('click',()=>{
  const blob=new Blob([JSON.stringify(exportReport(),null,2)+'\n'],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download='jali-laptop-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
function ready(){if(!JaliHeadDemo.getState().ready)return;loaded=true;$('measure').disabled=false;document.querySelectorAll('[data-clip]').forEach(b=>b.disabled=false);status('Ready. Listen first, then measure a recording.');}
window.addEventListener('jali-head-ready',ready);ready();
window.JaliCheckpoint={exportReport,getRuns:()=>structuredClone(runs),isMeasuring:()=>Boolean(active),getMeasurementPhase:()=>active?.phase??null};
