import {Muxer,ArrayBufferTarget} from 'webm-muxer';
// Deterministic, bounded offline export. Rendering speed does not change AV time.
export function recordingController({audio,canvas,head,getClip,getSettings,lock,offer,clear,status}){
 let running=false,cancelled=false,frames=[],bytes=0;
 const check=()=>{if(cancelled)throw new DOMException('Export cancelled; incomplete movie discarded','AbortError');};
 async function start(){
  if(running)throw Error('An export is already active');
  const clip=getClip(),settings=structuredClone(getSettings());if(!clip)throw Error('Select a completed verified recording first');
  if(!window.VideoEncoder||!window.AudioEncoder||!window.AudioData||!window.VideoFrame||!window.OfflineAudioContext||!crypto.subtle)throw Error('Offline video encoding requires a current Chrome browser and HTTPS/localhost. JSON/CSV export still works.');
  const fps=settings.fps,size=settings.resolution;
  if(![15,24,30,60].includes(fps)||![256,512,768].includes(size)||!(clip.duration>0&&clip.duration<=60))throw Error('Invalid video export budget');
  running=true;cancelled=false;frames=[];bytes=0;lock(true);clear();let videoEncoder,audioEncoder,failure=null,capture=false,videoChunks=0,audioChunks=0;
  const previousTime=audio.currentTime,previousPointerEvents=canvas.style.pointerEvents;canvas.style.pointerEvents='none';
  try{
   audio.pause();
   const response=await fetch(audio.currentSrc||audio.src);if(!response.ok)throw Error('Selected WAV is unavailable');const wav=await response.arrayBuffer();
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',wav)),b=>b.toString(16).padStart(2,'0')).join('');
   if(hash!==clip.audio.sha256||clip.analysis.audio_sha256!==hash)throw Error('Export WAV/cue identity mismatch');check();
   const decoded=await new OfflineAudioContext(1,1,48000).decodeAudioData(wav);
   if(decoded.numberOfChannels!==1||Math.abs(decoded.duration-clip.duration)>.025)throw Error('Export decoded duration/channel mismatch');
   const videoConfig={codec:'vp8',width:size,height:size,bitrate:4000000,framerate:fps,latencyMode:'realtime'};
   const audioConfig={codec:'opus',sampleRate:48000,numberOfChannels:1,bitrate:96000};
   if(!(await VideoEncoder.isConfigSupported(videoConfig)).supported||!(await AudioEncoder.isConfigSupported(audioConfig)).supported)throw Error('VP8/Opus encoding is unavailable in this browser');
   const target=new ArrayBufferTarget(),muxer=new Muxer({target,video:{codec:'V_VP8',width:size,height:size,frameRate:fps},audio:{codec:'A_OPUS',sampleRate:48000,numberOfChannels:1},firstTimestampBehavior:'offset'});
   const error=e=>{failure=e;};
   videoEncoder=new VideoEncoder({output:(chunk,meta)=>{try{if(chunk.timestamp!==Math.round(videoChunks/fps*1e6))throw Error('Encoded video timestamp diverged from source clock');muxer.addVideoChunk(chunk,meta);videoChunks++;}catch(e){failure=e;}},error});videoEncoder.configure(videoConfig);
   audioEncoder=new AudioEncoder({output:(chunk,meta)=>{try{muxer.addAudioChunk(chunk,meta);audioChunks++;}catch(e){failure=e;}},error});audioEncoder.configure(audioConfig);
   head.setCaptureMode(true,size);capture=true;const pcm=decoded.getChannelData(0),count=Math.ceil(clip.duration*fps);let sample=0;
   for(let i=0;i<count;i++){
    check();if(failure)throw failure;const time=i/fps;head.updateClock(time);
    const frame=new VideoFrame(canvas,{timestamp:Math.round(time*1e6),duration:Math.round(Math.min(1/fps,clip.duration-time)*1e6)});
    try{videoEncoder.encode(frame,{keyFrame:i%Math.max(1,fps*2)===0});}finally{frame.close();}
    frames.push({time,...structuredClone(head.getState().layers)});
    const until=Math.min(pcm.length,Math.ceil((i+1)/fps*48000));
    while(sample<until){const end=Math.min(pcm.length,sample+960),packet=new AudioData({format:'f32-planar',sampleRate:48000,numberOfFrames:end-sample,numberOfChannels:1,timestamp:Math.round(sample/48000*1e6),data:pcm.subarray(sample,end)});try{audioEncoder.encode(packet);}finally{packet.close();}sample=end;}
    if(videoEncoder.encodeQueueSize>=2)await videoEncoder.flush();if(audioEncoder.encodeQueueSize>=8)await audioEncoder.flush();
    status(`Rendering export frame ${i+1} / ${count}. Cancel discards incomplete output.`);
   }
   await videoEncoder.flush();await audioEncoder.flush();check();if(failure)throw failure;if(videoChunks!==frames.length||audioChunks<1)throw Error('Encoder dropped output; incomplete movie discarded');muxer.finalize();bytes=target.buffer.byteLength;
   offer('performance.webm',new Blob([target.buffer],{type:'video/webm'}));
   offer('recorded-frames.json',new Blob([JSON.stringify({schema:'jali-recorded-frames-v2',mode:'offline-fixed-media-clock',session_id:clip.id,audio_sha256:hash,text_sha256:clip.text_sha256,rig:clip.rig,settings,fps,encoded_video_frames:videoChunks,width:size,height:size,frames,recorded_end:clip.duration,full_session_recorded:true,audio_codec:'Opus, resampled to 48000 Hz',video_codec:'VP8',limits:'Each video frame samples the same source-WAV media clock. Encoded audio has codec delay/padding and is not bit-identical PCM. Not physical AV or universal DCC certification.'},null,2)],{type:'application/json'}));
   status('Offline export ready: download WebM and its matching fixed-clock frames below.');
  }catch(e){status(e.message);throw e;}
  finally{try{for(const encoder of [videoEncoder,audioEncoder])if(encoder&&encoder.state!=='closed')encoder.close();if(capture)head.setCaptureMode(false);head.updateClock(previousTime);}finally{canvas.style.pointerEvents=previousPointerEvents;running=false;lock(false);}}
 }
 window.addEventListener('beforeunload',()=>{cancelled=true;});
 return {start,stop:()=>{cancelled=true;},get active(){return running;},get stats(){return {frames:frames.length,bytes};}};
}
