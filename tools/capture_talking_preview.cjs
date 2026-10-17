// Actual new local WAV + dialog-derived cues -> deterministic WebGL frames -> MP4.
// Developer-only FFmpeg rendering; browser WebM export still requires current Chrome.
const fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process'),{createHash}=require('node:crypto');
(async()=>{
 const base=process.argv[2]||'http://127.0.0.1:8082',out=path.resolve(process.argv[3]||'artifacts/talking-preview');fs.mkdirSync(out,{recursive:true});
 const browser=await require('./test_browser.cjs').launch(),context=await browser.newContext({viewport:{width:1200,height:1000}}),errors=[];
 const text='Hello. Here is our updated local character. Watch the eyes and the hair as I speak. Please bring my blue paper bag.';
 try{
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  await page.goto(base+'?preset=low');await page.waitForFunction(()=>window.JaliCreative&&window.JaliStudio&&JaliHeadDemo.getState().ready&&!document.querySelector('#generate').disabled,null,{timeout:60000});
  await page.fill('#text',text);await page.click('#generate');await page.waitForFunction(()=>JaliStudio.getState().busy);await page.waitForFunction(()=>!JaliStudio.getState().busy,null,{timeout:180000});
  const state=await page.evaluate(()=>JaliStudio.getState());if(!state.verified)throw Error(await page.locator('#error').textContent());
  const clip=await(await context.request.get(base+'/sessions/'+state.selectedId+'/manifest.json')).json();
  const wav=await(await context.request.get(base+clip.file)).body();if(createHash('sha256').update(wav).digest('hex')!==clip.audio.sha256||clip.analysis.audio_sha256!==clip.audio.sha256||clip.text!==text)throw Error('Actual WAV/text/cue binding failed');
  fs.writeFileSync(path.join(out,'speech.wav'),wav);
  async function setup(){await page.evaluate(()=>{document.querySelector('#audio').pause();JaliHeadDemo.setAppearance({lighting:'soft',background:'slate',camera:'portrait',exposure:1,skin:.75,eyes:.12,fxaa:false});JaliHeadDemo.setCaptureMode(true,512);});}
  await setup();const enhanced=await page.evaluate(()=>JaliHeadDemo.getState().surfaceShading);
  if(enhanced?.eyeMeshes<1||enhanced?.hairMeshes<1||enhanced.version!=='physical-eyes-hair-cards-v1')throw Error('Enhanced eye/hair shader was not applied');
  fs.writeFileSync(path.join(out,'after.png'),Buffer.from((await page.evaluate(()=>JaliHeadDemo.capture(.4))).split(',')[1],'base64'));
  const fps=15,count=Math.ceil(clip.duration*fps),frames=path.join(out,'frames');fs.mkdirSync(frames,{recursive:true});for(const name of fs.readdirSync(frames))if(/^frame-\d{5}\.png$/.test(name))fs.unlinkSync(path.join(frames,name));const poses=[];
  for(let i=0;i<count;i++){
   const result=await page.evaluate(t=>({image:JaliHeadDemo.capture(t),layers:JaliHeadDemo.getState().layers}),i/fps);
   fs.writeFileSync(path.join(frames,`frame-${String(i).padStart(5,'0')}.png`),Buffer.from(result.image.split(',')[1],'base64'));poses.push({time:i/fps,...result.layers});
   if(i%30===0)console.log('Rendered actual face',i,'/',count);
  }
  const asset=await page.evaluate(()=>JaliHeadDemo.getState().renderAsset);
  // Same WAV, same camera/settings/clock; original shading is an explicit URL mode.
  await page.goto(base+'?preset=low&surface=original');await page.waitForFunction(()=>window.JaliCreative&&window.JaliStudio&&JaliHeadDemo.getState().ready&&!document.querySelector('#generate').disabled,null,{timeout:60000});
  await page.evaluate(id=>JaliStudio.loadExisting(id),clip.id);await setup();
  fs.writeFileSync(path.join(out,'before.png'),Buffer.from((await page.evaluate(()=>JaliHeadDemo.capture(.4))).split(',')[1],'base64'));
  if(errors.length)throw Error('Browser errors: '+JSON.stringify(errors));
  const python=process.env.JALI_PYTHON||path.resolve(process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python');
  const video=path.join(out,'talking-face.mp4');
  execFileSync(python,['-c',"import imageio_ffmpeg,subprocess,sys;subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner','-loglevel','error','-framerate','15','-i',sys.argv[1],'-i',sys.argv[2],'-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-frames:v',sys.argv[4],'-movflags','+faststart',sys.argv[3]],check=True);subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',sys.argv[3],'-f','null','-'],check=True);checks=subprocess.check_output([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',sys.argv[3],'-map','0:v:0','-f','framemd5','-'],text=True);assert sum(1 for line in checks.splitlines() if line.strip() and not line.startswith('#'))==int(sys.argv[4]),'Encoded frame count mismatch'",path.join(frames,'frame-%05d.png'),path.join(out,'speech.wav'),video,String(count)],{timeout:180000,stdio:'inherit'});
  const evidence={schema:'jali-talking-preview-v1',fixture:false,text,session_id:clip.id,audio_sha256:clip.audio.sha256,text_sha256:clip.text_sha256,rig:clip.rig,render_asset:asset,surface_shading:enhanced,appearance:{lighting:'soft',camera:'portrait',resolution:512},fps,frames:count,duration:clip.duration,video_sha256:createHash('sha256').update(fs.readFileSync(video)).digest('hex'),all_streams_ffmpeg_decoded:true,encoded_video_frames:count,encoded_frames_verified_by_framemd5:true,poses,browser_errors:errors,limits:'Actual WebGL/stock CPU speech; not generated imagery. Offline fixed-WAV-clock render, not physical AV, subjective realism approval, native appearance parity or measured i5 performance.'};
  fs.writeFileSync(path.join(out,'evidence.json'),JSON.stringify(evidence,null,2));console.log('Actual talking video ready:',video);
 }finally{await context.close();await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
