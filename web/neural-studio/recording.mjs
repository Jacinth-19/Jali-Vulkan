// Browser real-time capture, not an offline/gapless or physical AV guarantee.
export function recordingController({audio,canvas,head,getClip,getSettings,lock,offer,clear,status}){
 let context,source,destination,recorder=null,tracks=[],timer,observations=[],aborted=false;
 const finish=(reason=null)=>{if(!recorder)return;if(reason){aborted=true;status(reason);}if(recorder.state!=='inactive')recorder.stop();};
 const onRender=e=>{if(recorder?.state==='recording')observations.push({time:e.detail.audioTime,...structuredClone(head.getState().layers)});};
 async function start(){
  const clip=getClip(),settings=structuredClone(getSettings());if(!clip)throw Error('Select a completed verified recording first');
  if(recorder)throw Error('A recording is already active');
  if(!window.MediaRecorder||!canvas.captureStream)throw Error('Video recording is unavailable in this browser; JSON/CSV export still works');
  const mime=['video/webm;codecs=vp9,opus','video/webm;codecs=vp8,opus','video/webm'].find(m=>MediaRecorder.isTypeSupported(m));if(!mime)throw Error('This browser has no supported WebM encoder');
  lock(true);clear();aborted=false;observations=[];
  try{
   audio.pause();audio.playbackRate=1;if(audio.currentTime!==0){await new Promise((resolve,reject)=>{const timeout=setTimeout(()=>{cleanup();reject(Error('Recording seek timed out'));},5000);function cleanup(){clearTimeout(timeout);audio.removeEventListener('seeked',done);}function done(){cleanup();resolve();}audio.addEventListener('seeked',done);audio.currentTime=0;});}
   if(!context){context=new AudioContext();source=context.createMediaElementSource(audio);source.connect(context.destination);destination=context.createMediaStreamDestination();source.connect(destination);}
   await context.resume();head.updateClock(0);
   const video=canvas.captureStream(30);tracks=[...video.getVideoTracks(),...destination.stream.getAudioTracks().map(t=>t.clone())];
   recorder=new MediaRecorder(new MediaStream(tracks),{mimeType:mime,videoBitsPerSecond:4000000});
   const chunks=[];recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
   recorder.onerror=()=>finish('Encoder failed; the incomplete recording was discarded');
   const end=()=>finish(),seek=()=>finish('Seeking interrupted capture; recording discarded'),pause=()=>{if(!audio.ended&&recorder?.state==='recording')finish('Playback paused; recording discarded');};
   const rate=()=>finish('Playback rate changed; recording discarded'),badAudio=()=>finish('Audio failed; recording discarded');
   audio.addEventListener('ratechange',rate);audio.addEventListener('error',badAudio);audio.addEventListener('ended',end);audio.addEventListener('seeking',seek);audio.addEventListener('pause',pause);window.addEventListener('jali-render',onRender);
   const priorDiagnostics=window.JALI_RENDER_DIAGNOSTICS;window.JALI_RENDER_DIAGNOSTICS=true;
   recorder.onstop=()=>{
    clearTimeout(timer);audio.removeEventListener('ratechange',rate);audio.removeEventListener('error',badAudio);audio.removeEventListener('ended',end);audio.removeEventListener('seeking',seek);audio.removeEventListener('pause',pause);window.removeEventListener('jali-render',onRender);window.JALI_RENDER_DIAGNOSTICS=priorDiagnostics;
    for(const t of tracks)t.stop();tracks=[];recorder=null;lock(false);
    if(!aborted&&chunks.length){offer('performance.webm',new Blob(chunks,{type:mime}));offer('recorded-frames.json',new Blob([JSON.stringify({schema:'jali-recorded-frames-v1',session_id:clip.id,audio_sha256:clip.audio.sha256,rig:clip.rig,settings,capture_frame_rate_requested:30,width:canvas.width,height:canvas.height,audio_context_sample_rate:context.sampleRate,frames:observations,recorded_end:audio.currentTime,full_session_recorded:audio.ended,limits:'Render-submission media-clock samples, potentially sparse/dropped under load. WebM contains the same media-element audio; not physical AV certification or deterministic offline rendering.'},null,2)],{type:'application/json'}));status('Capture ready: download WebM and its actual frame timeline below.');}
   };
   recorder.start(250);observations.push({time:0,...structuredClone(head.getState().layers)});await audio.play();
   timer=setTimeout(()=>finish('Capture deadline exceeded; incomplete recording discarded'),(clip.duration+15)*1000);status('Recording the selected WAV from the start. Do not pause or seek.');
  }catch(e){if(recorder){finish(e.message);}else{for(const t of tracks)t.stop();tracks=[];lock(false);}throw e;}
 }
 window.addEventListener('beforeunload',()=>{aborted=true;finish();for(const t of tracks)t.stop();context?.close();});
 return {start,stop:()=>finish(),get active(){return !!recorder;}};
}
