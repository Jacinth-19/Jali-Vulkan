// Actual M2 integration: real browser form -> CPU model -> Rhubarb -> actual mesh.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),zlib=require('node:zlib');
const {execFileSync}=require('node:child_process');
const {createHash}=require('node:crypto');
const {chromium:playwright}=require('playwright-core');
const chromium=require('@sparticuz/chromium');
(async()=>{
  const base=process.argv[2]||'http://127.0.0.1:8082',origin=new URL(base).origin;
  const proof=path.resolve('artifacts/neural-studio/proof');fs.mkdirSync(proof,{recursive:true});
  const channel=process.env.JALI_BROWSER_CHANNEL;
  const support=path.resolve('.cache/runtime/browser');fs.mkdirSync(support,{recursive:true});
  if(!channel){
    const archive=path.join(support,'support.tar');
    fs.writeFileSync(archive,zlib.brotliDecompressSync(fs.readFileSync(path.join(__dirname,'node_modules/@sparticuz/chromium/bin/al2023.tar.br'))));
    execFileSync('tar',['-xf',archive,'-C',support]);
  }
  const browser=await playwright.launch(channel?{channel,headless:true,args:['--enable-unsafe-swiftshader']}:{
    executablePath:await chromium.executablePath(),args:chromium.args.filter(a=>a!=='--disable-web-security'),headless:true,
    env:{...process.env,LD_LIBRARY_PATH:`${support}/lib:/tmp:${process.env.LD_LIBRARY_PATH||''}`}});
  const context=await browser.newContext({viewport:{width:1440,height:1100},deviceScaleFactor:1});
  const page=await context.newPage(),errors=[],external=[],sessions=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  page.on('request',r=>{if(/^https?:/.test(r.url())&&!r.url().startsWith(origin+'/'))external.push(r.url());});
  page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});
  try{
    await page.goto(base,{waitUntil:'networkidle'});
    await page.waitForFunction(()=>window.JaliHeadDemo?.getState().ready&&!document.querySelector('#generate').disabled,null,{timeout:60000});
    for(const [preset,size] of [['low',256],['high',768],['balanced',512]]){
      await page.selectOption('#quality-preset',preset);
      const q=await page.evaluate(()=>({quality:JaliStudio.getState().quality,canvas:JaliHeadDemo.getDiagnostics().canvas}));
      if(q.quality.resolution!==size||Math.max(q.canvas.width,q.canvas.height)>size)throw Error('Actual preset framebuffer not bounded');
    }
    // Golden articulation recordings retain baseline; Clear is tested separately.
    await page.selectOption('#art-profile','baseline');
    const model=await page.evaluate(()=>JaliHeadDemo.getState().modelStats);
    if(model.faceControls!==66||model.bones!==67)throw new Error('Detailed character missing');
    // Real UI cancellation, then retry through the same bounded worker.
    await page.locator('#mood').selectOption('warm');await page.locator('#gaze').selectOption('left');
    await page.locator('#text').fill('Cancel this generated performance before it can play.');
    await page.locator('#generate').click();
    await page.waitForFunction(()=>JaliStudio.getState().currentJob&&!document.querySelector('#cancel').disabled);
    const cancelledId=await page.evaluate(()=>JaliStudio.getState().currentJob);
    await page.locator('#cancel').click();
    await page.waitForFunction(()=>!JaliStudio.getState().busy&&JaliStudio.getState().phase==='cancelled',null,{timeout:20000});
    const cancelled=await (await context.request.get(`${base}/api/jobs/${cancelledId}`)).json();
    if(cancelled.state!=='cancelled'||(await context.request.get(`${base}/sessions/${cancelledId}/audio.wav`)).status()!==404)throw new Error('Cancelled output exposed');
    const cancelledFace=await page.evaluate(()=>JaliHeadDemo.getState());
    if(await page.locator('#audio').getAttribute('src')||Object.values(cancelledFace.pose).some(w=>w!==0)||cancelledFace.gazeBones.some(b=>b.delta.x||b.delta.y))throw new Error('Cancellation retained audio or non-neutral pose');
    const defaultTexts=[
      'Hello, this is the connected local voice and face test. Please bring my blue paper bag.',
      'The new recording has its own timing. We can pause, jump back, and replay the same face.'
    ];
    const corpus=JSON.parse(fs.readFileSync('tests/fixtures/neural-articulation.json'));
    const reviewMode=process.env.JALI_REVIEW==='1';
    const texts=reviewMode?corpus.cases.map(c=>c.text):defaultTexts;
    for(const text of texts){
      await page.locator('#text').fill(text);await page.locator('#generate').click();
      await page.waitForFunction(()=>JaliStudio.getState().busy);
      const cleared=await page.evaluate(()=>({id:JaliHeadDemo.getState().sessionId,src:document.querySelector('#audio').getAttribute('src')}));
      if(cleared.id||cleared.src)throw new Error('New request retained previous playback');
      await page.waitForFunction(()=>!JaliStudio.getState().busy,null,{timeout:200000});
      const state=await page.evaluate(()=>JaliStudio.getState());
      if(!state.verified||state.phase!=='ready')throw new Error(await page.locator('#error').textContent());
      const id=state.selectedId;
      const response=await context.request.get(`${base}/sessions/${id}/manifest.json`);const clip=await response.json();
      if(clip.text!==text||clip.analysis.audio_sha256!==clip.audio.sha256||clip.tts.providers.join()!=='CPUExecutionProvider')throw new Error('Wrong text/audio/CPU binding');
      const wav=await context.request.get(`${base}${clip.file}`);
      if(createHash('sha256').update(await wav.body()).digest('hex')!==clip.audio.sha256)throw new Error('WAV provenance mismatch');
      await page.waitForFunction(()=>Number(document.querySelector('#face').dataset.audioTime)>0.2,null,{timeout:20000});
      if(await page.locator('#audio').getAttribute('data-session')!==id)throw new Error('Player session differs from face');
      await page.locator('#audio').evaluate(a=>a.pause());
      await page.locator('#life').uncheck();
      const shape=clip.cues.filter(c=>c.value==='A').sort((a,b)=>(b.end-b.start)-(a.end-a.start))[0];
      if(!shape)throw new Error('Speech lacks expected closure cue');
      const seek=shape.start+Math.min(0.01,(shape.end-shape.start)/4);
      await page.locator('#audio').evaluate((a,t)=>a.currentTime=t,seek);
      await page.waitForFunction(t=>Math.abs(Number(document.querySelector('#face').dataset.audioTime)-t)<0.025,seek);
      const posed=await page.evaluate(t=>{JaliHeadDemo.capture(t);return JaliHeadDemo.getState();},seek);
      if(!posed.activeMorphs.some(m=>m.values.viseme_PP>0.5))throw new Error('Actual closed-mouth morph not driven');
      await page.locator('#mood').selectOption('neutral');
      const neutralClosure=await page.evaluate(t=>JaliHeadDemo.capture(t),seek);
      await page.locator('#mood').selectOption('warm');
      const warmClosure=await page.evaluate(t=>JaliHeadDemo.capture(t),seek);
      if(neutralClosure!==warmClosure)throw new Error('Warm layer changed full-closure pixels');
      await page.locator('#mood').selectOption('neutral');
      await page.locator('#gaze').selectOption('left');
      const leftGaze=await page.evaluate(t=>({image:JaliHeadDemo.capture(t),bones:JaliHeadDemo.getState().gazeBones}),seek);
      await page.locator('#gaze').selectOption('right');
      const rightGaze=await page.evaluate(t=>({image:JaliHeadDemo.capture(t),bones:JaliHeadDemo.getState().gazeBones}),seek);
      if(leftGaze.bones.length!==2||!leftGaze.bones.every(b=>Math.abs(b.delta.y-.08)<1e-6)||!rightGaze.bones.every(b=>Math.abs(b.delta.y+.08)<1e-6)||leftGaze.image===rightGaze.image)throw new Error('Eye-bone gaze not rendered');
      await page.locator('#gaze').selectOption('forward');
      await page.locator('#sync').uncheck();
      const disabled=await page.evaluate(t=>{JaliHeadDemo.capture(t);return JaliHeadDemo.getState();},seek);
      if(disabled.activeMorphs.some(m=>Object.keys(m.values).some(k=>k.startsWith('viseme_'))))throw new Error('Speech weights did not reset');
      await page.locator('#sync').check();
      await page.locator('#audio').evaluate(async a=>{a.currentTime=a.duration-.15;await a.play();});
      await page.waitForFunction(()=>document.querySelector('#audio').ended&&document.querySelector('#face').dataset.shape==='X');
      sessions.push(clip);console.log('New-text session passed',id,clip.duration.toFixed(2),'seconds,',clip.cues.length,'mouth cues');
    }
    if(new Set(sessions.map(c=>c.id)).size!==sessions.length||new Set(sessions.map(c=>c.audio.sha256)).size!==sessions.length)throw new Error('New request reused previous recording');
    // Replay the first immutable history item after generating a second one.
    await page.locator(`#history [data-session="${sessions[0].id}"]`).click();
    await page.waitForFunction(id=>JaliHeadDemo.getState().sessionId===id&&document.querySelector('#audio').currentTime>.1,sessions[0].id);
    await page.locator('#audio').evaluate(a=>a.pause());
    await page.locator('#stop').click();
    const stopped=await page.evaluate(()=>({head:JaliHeadDemo.getState(),studio:JaliStudio.getState(),src:document.querySelector('#audio').getAttribute('src')}));
    if(stopped.src||stopped.head.sessionId||stopped.studio.verified||Object.values(stopped.head.pose).some(w=>w!==0)||stopped.head.gazeBones.some(b=>b.delta.x||b.delta.y))throw new Error('Stop left stale audio or face');
    await page.locator(`#history [data-session="${sessions[0].id}"]`).click();
    await page.waitForFunction(id=>JaliHeadDemo.getState().sessionId===id,sessions[0].id);
    await page.locator('#audio').evaluate(a=>a.pause());
    await page.screenshot({path:path.join(proof,'desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});await page.waitForTimeout(200);
    if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Mobile overflow');
    await page.screenshot({path:path.join(proof,'mobile.png'),fullPage:true});
    if(errors.length||external.length)throw new Error(JSON.stringify({errors,external}));
    if(reviewMode){
      const {SHAPES,sampleVisemes}=await import('../web/neural-head/visemes.mjs');
      const review=path.resolve('artifacts/neural-review');fs.mkdirSync(path.join(review,'frames'),{recursive:true});
      const observed=new Set(),frames=[];
      await page.locator('#life').uncheck();await page.locator('#mood').selectOption('neutral');
      await page.locator('#trim').evaluate(el=>{el.value='0';el.dispatchEvent(new Event('input'));});
      await page.evaluate(()=>JaliHeadDemo.setCaptureMode(true,512));
      try{
        for(let index=0;index<sessions.length;index++){
          const clip=sessions[index];
          for(const value of Object.keys(SHAPES)){
            const cue=clip.cues.filter(c=>c.value===value).sort((a,b)=>(b.end-b.start)-(a.end-a.start))[0];
            if(!cue)continue;
            observed.add(value);const time=cue.start+(cue.end-cue.start)*0.5;
            const {image,state}=await page.evaluate(({time,index})=>({image:JaliHeadDemo.capture(time,index),state:JaliHeadDemo.getState()}),{time,index});
            const expected=sampleVisemes(clip.cues,time).weights;
            for(const [key,weight] of Object.entries(expected)){
              if(weight>0.01&&!state.activeMorphs.some(m=>Math.abs((m.values[key]||0)-weight)<0.001))throw new Error(`Retarget mismatch ${value}/${key}`);
            }
            const file=`frames/${corpus.cases[index].id}-${value}.png`;
            fs.writeFileSync(path.join(review,file),Buffer.from(image.split(',')[1],'base64'));
            frames.push({case:corpus.cases[index].id,value,time,file,weights:expected});
          }
          // All short estimated cues must retain their central target pose.
          for(const cue of clip.cues){
            const at=sampleVisemes(clip.cues,cue.start+(cue.end-cue.start)*0.5);
            for(const [key,weight] of Object.entries(SHAPES[cue.value].weights))if(Math.abs((at.weights[key]||0)-weight)>1e-6)throw new Error('Short cue lost its central hold');
          }
        }
      }finally{await page.evaluate(()=>JaliHeadDemo.setCaptureMode(false)).catch(()=>{});}
      fs.writeFileSync(path.join(review,'articulation.json'),JSON.stringify({
        method:'Actual new CPU speech, estimated Rhubarb cues, deterministic neutral-pose renders',
        independently_verified_phoneme_alignment:false,human_review_completed:false,
        quality_score:null,observed_classes:[...observed],missing_classes:Object.keys(SHAPES).filter(v=>!observed.has(v)),
        contract_checks:['central hold survives short cues','actual named morph weights match retarget','neutral styling and procedural motion disabled'],
        corpus,sessions,frames
      },null,2)+'\n');
      console.log('M3 review frames',frames.length,'estimated classes',[...observed].join(','));
    }
    if(process.env.EXPORT_VIDEO==='1'){
      await page.evaluate(()=>JaliHeadDemo.setCaptureMode(true,512));
      const temp=fs.mkdtempSync(path.join(os.tmpdir(),'jali-studio-frames-'));
      try{
        const clip=sessions[0],fps=15,frames=Math.ceil(clip.duration*fps);
        for(let i=0;i<frames;i++){
          const data=await page.evaluate(t=>JaliHeadDemo.capture(t,0,'image/jpeg'),i/fps);
          fs.writeFileSync(path.join(temp,`frame-${String(i).padStart(4,'0')}.jpg`),Buffer.from(data.split(',')[1],'base64'));
          if(i%30===0)console.log('Rendered',i,'/',frames);
        }
        const wav=path.resolve('artifacts/neural-studio-sessions',clip.id,'audio.wav');
        const out=path.join(proof,'new-text-performance.mp4');
        execFileSync(process.env.JALI_PYTHON||path.resolve(process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python'),['-c',`import imageio_ffmpeg,subprocess;subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner','-loglevel','error','-framerate','15','-i',${JSON.stringify(path.join(temp,'frame-%04d.jpg'))},'-i',${JSON.stringify(wav)},'-c:v','libx264','-crf','20','-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-shortest','-movflags','+faststart',${JSON.stringify(out)}],check=True)`],{timeout:60000});
        fs.copyFileSync(path.join(temp,'frame-0000.jpg'),path.join(proof,'poster.jpg'));
        fs.writeFileSync(path.join(proof,'video-export.json'),JSON.stringify({session_id:clip.id,audio_sha256:clip.audio.sha256,rig:clip.rig,fps,frames,
          mp4_sha256:createHash('sha256').update(fs.readFileSync(out)).digest('hex'),method:'Offline browser capture of same new-text session, muxed with that session WAV'},null,2)+'\n');
      }finally{fs.rmSync(temp,{recursive:true,force:true});await page.evaluate(()=>JaliHeadDemo.setCaptureMode(false)).catch(()=>{});}
    }
    if(errors.length||external.length)throw new Error(JSON.stringify({errors,external}));
    // Real bounded sentence batching: interrupt during playback, then complete
    // another request. This is intentionally not called incremental Kokoro.
    const streamText=Array(4).fill('Mama packed my blue paper bag and brought it back to me, while five vivid voices moved very fast beside the bright blue window today.').join(' ');
    if(streamText.length<=500||streamText.length>1000)throw Error('Long-paragraph integration must exercise the expanded budget');
    await page.locator('#batch').check();await page.locator('#text').fill(streamText);await page.locator('#generate').click();
    await page.waitForFunction(()=>JaliStudio.getState().streamStats?.chunks.length===1&&document.querySelector('#audio').currentTime>.1,null,{timeout:120000});
    const interruptedId=await page.evaluate(()=>JaliStudio.getState().currentJob);
    const pending=await (await context.request.get(`${base}/api/jobs/${interruptedId}`)).json();
    if(pending.state!=='running'||pending.produced>=3||pending.chunks.length>2)throw new Error('First batch did not play before bounded producer completion');
    await page.locator('#stop').click();
    await page.waitForFunction(()=>!JaliStudio.getState().busy&&JaliStudio.getState().phase==='cancelled',null,{timeout:20000});
    if(await page.locator('#audio').getAttribute('src'))throw new Error('Stream stop retained stale audio');
    await page.locator('#text').fill(streamText);await page.locator('#generate').click();
    await page.waitForFunction(()=>JaliStudio.getState().busy);
    await page.waitForFunction(()=>!JaliStudio.getState().busy,null,{timeout:240000});
    const stream=await page.evaluate(()=>JaliStudio.getState());
    if(stream.phase!=='ready'||!stream.verified||stream.streamStats.chunks.length!==4)throw new Error('Sentence-batched retry failed: '+JSON.stringify({stream,error:await page.locator('#error').textContent()}));
    const joined=await (await context.request.get(`${base}/sessions/${stream.selectedId}/manifest.json`)).json();
    const joinedWav=await context.request.get(`${base}${joined.file}`);
    if(joined.stream.chunks!==4||joined.audio.sha256!==createHash('sha256').update(await joinedWav.body()).digest('hex')||joined.stream.samples!==stream.streamStats.chunks[3].end_sample)throw new Error('Combined sentence audio lost provenance/sample offsets');
    fs.writeFileSync(path.join(proof,'stream-check.json'),JSON.stringify({passed:true,mode:'sentence-batched',first_batch_before_all_produced:true,max_pending:2,cancel_then_retry:true,input_characters:streamText.length,prebuffer_hits:stream.streamStats.prebufferHits,prefetch_availability_limited:stream.streamStats.downloadedAhead===0,combined_audio_sha256:joined.audio.sha256,stream:joined.stream,observations:stream.streamStats,limits:'Observed automation timings, not gapless playback or target-laptop performance acceptance'},null,2)+'\n');
    await page.locator('#batch').uncheck();
    if(errors.length||external.length)throw new Error(JSON.stringify({errors,external}));
    // User-facing export with a freshly synthesized real corpus WAV, not a fixture.
    await page.locator(`#history button[data-session="${sessions[0].id}"]`).first().click();
    await page.evaluate(()=>document.querySelector('#audio').pause());
    await page.locator('#record-start').click();await page.waitForFunction(()=>JaliCreative.recording.active,null,{timeout:15000});
    await page.waitForFunction(()=>!JaliCreative.recording.active&&!!document.querySelector('a[download="performance.webm"]'),null,{timeout:45000});
    for(const [name,target] of [['performance.webm','user-export.webm'],['recorded-frames.json','user-export-frames.json']]){
      const pending=page.waitForEvent('download');await page.locator(`a[download="${name}"]`).click();await(await pending).saveAs(path.join(proof,target));
    }
    const exported=JSON.parse(fs.readFileSync(path.join(proof,'user-export-frames.json')));
    if(!exported.full_session_recorded||exported.audio_sha256!==sessions[0].audio.sha256||exported.frames.length<2)throw Error('Genuine user video export failed WAV/clock binding');
    if(errors.length||external.length)throw new Error(JSON.stringify({errors,external}));
    fs.writeFileSync(path.join(proof,'browser-check.json'),JSON.stringify({passed:true,model,web_security_enabled:true,external_requests:external,errors,
      checks:[`${sessions.length} real form submissions`,'new CPU neural synthesis for each text','actual WAV analyzed with its dialog','downloaded WAV hash verified in browser','audio/face IDs match','actual closure morph','seek','sync off clears speech weights','natural end rests','old session replays with its own cues','mobile layout','cancel real generation hides partial media','cancel then retry','warm/full-closure pixel equality','left/right gaze changes actual render','stop clears audio/morphs/gaze','real sentence batching starts before producer completion','batch stop/cancel then retry','combined PCM offsets/hash verified'],
      sessions:sessions.map(c=>({id:c.id,text:c.text,audio_sha256:c.audio.sha256,duration:c.duration,cues:c.cues.length,total_seconds:c.total_seconds}))},null,2)+'\n');
    fs.rmSync(path.join(proof,'failure.png'),{force:true});
    console.log('M2/M3 real neural studio browser checks passed');
  }catch(error){await page.screenshot({path:path.join(proof,'failure.png'),fullPage:true}).catch(()=>{});throw error;}
  finally{await browser.close();}
})().catch(e=>{console.error(e);if(process.env.GITHUB_ACTIONS==='true')console.log('::error title=Neural browser failure::'+String(e.stack||e).replaceAll('%','%25').replaceAll('\r','%0D').replaceAll('\n','%0A'));process.exitCode=1;});
