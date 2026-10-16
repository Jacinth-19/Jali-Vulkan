// Fixed public-corpus live playback measurements. No model downloads or automatic upload.
const fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib');
const {execFileSync}=require('node:child_process'),{createHash}=require('node:crypto');
const {chromium}=require('playwright-core');
(async()=>{
 const [base,output,repeatArg,channel,headlessArg]=process.argv.slice(2),repeats=Number(repeatArg);
 if(!base||!output||![1,2,3].includes(repeats))throw Error('Invalid benchmark parameters');
 const corpus=JSON.parse(fs.readFileSync('tests/fixtures/neural-articulation.json'));
 let launch={channel,headless:headlessArg==='true'};
 if(channel==='sandbox'){
   const packaged=require('@sparticuz/chromium'),support=path.resolve('.cache/runtime/browser');fs.mkdirSync(support,{recursive:true});
   const archive=path.join(support,'support.tar');fs.writeFileSync(archive,zlib.brotliDecompressSync(fs.readFileSync(path.join(__dirname,'node_modules/@sparticuz/chromium/bin/al2023.tar.br'))));execFileSync('tar',['-xf',archive,'-C',support]);
   launch={executablePath:await packaged.executablePath(),headless:true,args:packaged.args.filter(a=>a!=='--disable-web-security'),env:{...process.env,LD_LIBRARY_PATH:`${support}/lib:/tmp:${process.env.LD_LIBRARY_PATH||''}`}};
 } else if(launch.headless) launch.args=['--enable-unsafe-swiftshader'];
 const browser=await chromium.launch(launch),samples=[],errors=[],outside=[],started=performance.now();
 try{
   const page=await browser.newPage({viewport:{width:1280,height:1000}});
   page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
   page.on('request',r=>{if(/^https?:/.test(r.url())&&!r.url().startsWith(base+'/'))outside.push(r.url());});
   await page.goto(base,{waitUntil:'load'});
   await page.waitForFunction(()=>window.JaliHeadDemo?.getState().ready&&!document.querySelector('#generate').disabled,null,{timeout:60000});
   const readySeconds=(performance.now()-started)/1000;
   const {summarizeFrames}=await import('../web/playback-checkpoint/measurement.mjs');
   for(let repeat=1;repeat<=repeats;repeat++)for(const entry of corpus.cases){
     await page.locator('#text').fill(entry.text);await page.locator('#generate').click();
     await page.waitForFunction(()=>JaliStudio.getState().busy);
     await page.waitForFunction(()=>!JaliStudio.getState().busy,null,{timeout:200000});
     const state=await page.evaluate(()=>JaliStudio.getState());
     if(!state.verified||state.phase!=='ready')throw Error('Generation/analysis failed; inspect local server log');
     await page.locator('#audio').evaluate(a=>a.pause());
     const response=await page.request.get(`${base}/sessions/${state.selectedId}/manifest.json`),clip=await response.json();
     if(clip.text!==entry.text||clip.tts.providers.join()!=='CPUExecutionProvider'||clip.analysis.audio_sha256!==clip.audio.sha256)throw Error('Incorrect fixed-corpus or CPU/audio binding');
     const wav=await (await page.request.get(base+clip.file)).body();
     if(createHash('sha256').update(wav).digest('hex')!==clip.audio.sha256)throw Error('Downloaded audio hash mismatch');
     const name=`${entry.id}-${repeat}`;
     fs.writeFileSync(path.join(output,name+'.wav'),wav);
     fs.writeFileSync(path.join(output,name+'-clip.json'),JSON.stringify(clip,null,2));
     fs.writeFileSync(path.join(output,name+'-reference.json'),JSON.stringify({audio_sha256:clip.audio.sha256,text_sha256:clip.text_sha256,
       method:null,reviewer:'',source:'',independent_of_rhubarb:false,events:[],instructions:'Mark intervals by listening/waveform or independent aligner. Never copy Rhubarb timings. Events require start/end/class A-H/X/uncertainty_seconds. Pending is not evaluated.'},null,2));
     await page.locator('#life').uncheck();await page.locator('#sync').check();await page.locator('#mood').selectOption('neutral');
     await page.locator('#trim').evaluate(el=>{el.value='0';el.dispatchEvent(new Event('input'));});
     const observation=await page.evaluate(()=>new Promise(resolve=>{
       const a=document.querySelector('#audio'),canvas=document.querySelector('#face');
       a.pause();a.playbackRate=1;a.currentTime=0;let done=false;
       const frames=[],diagnostics=JaliHeadDemo.getDiagnostics();window.JALI_RENDER_DIAGNOSTICS=true;
       const finish=reason=>{if(done)return;done=true;clearTimeout(timer);window.removeEventListener('jali-render',frame);a.removeEventListener('ended',ended);a.removeEventListener('pause',paused);a.removeEventListener('seeking',seek);a.removeEventListener('ratechange',rate);window.removeEventListener('resize',resize);document.removeEventListener('visibilitychange',hidden);canvas.removeEventListener('webglcontextlost',lost);window.JALI_RENDER_DIAGNOSTICS=false;a.pause();resolve({reason,frames,diagnostics});};
       const frame=e=>{const f=e.detail;if(f.playing&&!f.seeking&&f.audioTime>0&&!document.hidden&&(!frames.length||f.wallTime>frames.at(-1).wallTime))frames.push({wallTime:f.wallTime,audioTime:f.audioTime,renderMs:f.renderMs});};
       const ended=()=>finish('ended'),paused=()=>{if(a.paused&&!a.ended)finish('paused');},hidden=()=>{if(document.hidden)finish('tab hidden');},seek=()=>{if(frames.length)finish('seeked');},rate=()=>{if(a.playbackRate!==1)finish('rate changed');},resize=()=>finish('resized'),lost=()=>finish('context lost');
       window.addEventListener('jali-render',frame);a.addEventListener('ended',ended);a.addEventListener('pause',paused);a.addEventListener('seeking',seek);a.addEventListener('ratechange',rate);document.addEventListener('visibilitychange',hidden);window.addEventListener('resize',resize);canvas.addEventListener('webglcontextlost',lost);
       const timer=setTimeout(()=>finish('playback timeout'),90000);
       if(document.hidden)finish('tab hidden');else a.play().catch(()=>finish('playback blocked'));
     }));
     const {frames,...playback}=observation,metrics=summarizeFrames(frames);
     const sample={case:entry.id,repeat,audio_sha256:clip.audio.sha256,text_sha256:clip.text_sha256,duration_seconds:clip.duration,
       model_load_seconds:clip.tts.engine_load_seconds,dependency_import_seconds:clip.tts.dependency_import_seconds,
       generation_seconds:clip.generation_seconds,real_time_factor:clip.generation_seconds/clip.duration,
       analysis_seconds:clip.analysis_seconds,pipeline_seconds:clip.total_seconds,peak_worker_memory_mib:clip.tts.process_peak_rss_mib,
       memory_scope:clip.tts.memory_scope,providers:clip.tts.providers,rig:clip.rig,
       playback:{...playback,...metrics,valid_sample:playback.reason==='ended'&&metrics.rendered_frames>=2},files:{wav:name+'.wav',clip:name+'-clip.json',reference:name+'-reference.json'}};
     samples.push(sample);fs.writeFileSync(path.join(output,'browser.json'),JSON.stringify({browser_ready_seconds:readySeconds,channel,headless:launch.headless,samples,external_request_count:outside.length,browser_error_count:errors.length},null,2));
     console.log('Benchmarked',entry.id,'repeat',repeat,'pipeline',clip.total_seconds,'seconds; playback',sample.playback.reason);
     if(!sample.playback.valid_sample)throw Error('Interrupted or insufficient playback sample; retry without switching tabs');
   }
   if(errors.length||outside.length)throw Error('Browser errors or unexpected network activity; see local logs');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);if(process.env.GITHUB_ACTIONS==='true')console.log('::error title=Benchmark failure::'+String(e.stack||e).replaceAll('%','%25').replaceAll('\r','%0D').replaceAll('\n','%0A'));process.exitCode=1;});
