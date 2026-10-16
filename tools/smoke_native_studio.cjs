// Same verified WAV/audio clock, actual persistent native Vulkan response images.
const fs=require('node:fs'),path=require('node:path');
(async()=>{
 const browser=await require('./test_browser.cjs').launch();
 try{
  const page=await browser.newPage({viewport:{width:1400,height:1050}}),errors=[],external=[],origin=new URL(process.argv[2]).origin;
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url())&&!r.url().startsWith(origin+'/'))external.push(r.url());});
  await page.goto(process.argv[2]);await page.waitForFunction(()=>window.JaliHeadDemo?.getState().ready&&window.JaliStudio,null,{timeout:60000});
  const report=JSON.parse(fs.readFileSync('artifacts/neural-review/articulation.json')),clip=report.sessions[0],closure=report.frames.find(f=>f.case==='closures'&&f.value==='A');
  await page.evaluate(async id=>{await JaliStudio.loadExisting(id);document.querySelector('#life').checked=false;},clip.id);
  await page.selectOption('#renderer','native');
  await page.waitForFunction(id=>JaliStudio.getState().nativeInfo.lastSession===id,clip.id,{timeout:60000});
  await page.evaluate(t=>{document.querySelector('#audio').currentTime=t;},closure.time);
  await page.waitForFunction(t=>Math.abs(JaliStudio.getState().nativeInfo.lastTime-t)<.001,closure.time,{timeout:30000});
  const paused=await page.evaluate(()=>({studio:JaliStudio.getState(),head:JaliHeadDemo.getState(),renderer:JaliHeadDemo.getDiagnostics().activeRenderer}));
  if(!paused.studio.verified||paused.head.pose.viseme_PP!==.95||paused.renderer!=='native-vulkan')throw Error('Native clip/clock/pose verification failed');
  const out=path.resolve('artifacts/native-head-proof');fs.mkdirSync(out,{recursive:true});await page.locator('#native-face').screenshot({path:path.join(out,'native-studio.png')});
  await page.locator('#resume').click();await page.waitForFunction(t=>JaliStudio.getState().nativeInfo.lastTime>t+.25,closure.time,{timeout:30000});await page.evaluate(()=>document.querySelector('#audio').pause());
  const probes=await page.evaluate(async ({id,time,duration})=>{
    const config=await(await fetch('/api/config')).json();
    async function image(q,token=config.token){const response=await fetch('/api/native/frame?'+new URLSearchParams({id,time:String(time),life:'0',mood:'neutral',gaze:'forward',...q}),{headers:{'X-Jali-Token':token}});if(!response.ok)return {status:response.status};const bytes=await response.arrayBuffer(),hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');return {status:response.status,hash};}
    // Let the UI's single in-flight request settle before serialized direct probes.
    document.querySelector('#renderer').value='webgl';document.querySelector('#renderer').dispatchEvent(new Event('change'));await new Promise(r=>setTimeout(r,300));
    const normal=await image({}),warm=await image({mood:'warm'}),gaze=await image({gaze:'right'}),rest=await image({time:String(duration)}),neutral=await image({id:'neutral',time:'0'}),bad=await image({time:'nan'}),wrongToken=await image({},'wrong');
    return {normal,warm,gaze,rest,neutral,bad,wrongToken,device:config.native};
  },{id:clip.id,time:closure.time,duration:clip.duration});
  if(probes.normal.status!==200||probes.warm.hash!==probes.normal.hash||probes.gaze.hash===probes.normal.hash||probes.rest.hash!==probes.neutral.hash||probes.bad.status!==400||probes.wrongToken.status!==403)throw Error('Native image/control/bounds probes failed: '+JSON.stringify(probes));
  // Controlled protocol regression: a consumed/cancelled clip can expire while
  // its frame request is in flight. That stale 404 must not poison the new view.
  let injected=false;
  await page.route('**/api/native/frame?**',async route=>{
    if(injected)return route.continue();injected=true;
    await page.locator('#stop').click();
    await route.fulfill({status:404,contentType:'application/json',body:JSON.stringify({error:'Injected stale previous-session response'})});
  });
  await page.selectOption('#renderer','native');
  await page.waitForFunction(()=>JaliStudio.getState().nativeInfo.lastSession==='neutral',null,{timeout:30000});
  await page.unroute('**/api/native/frame?**');if(!injected)throw Error('Stale-response regression was not exercised');
  const state=await page.evaluate(()=>JaliStudio.getState());if(errors.length||external.length||state.nativeInfo.errors.length)throw Error(JSON.stringify({errors,external,native:state.nativeInfo.errors}));
  fs.writeFileSync(path.join(out,'native-browser.json'),JSON.stringify({passed:true,stale_previous_session_response_ignored:true,session_id:clip.id,audio_sha256:clip.audio.sha256,seek_time:closure.time,actual_native_frames:state.nativeInfo.frames,last_readback_ms:state.nativeInfo.lastMs,probes,errors,external,limits:'Real native image requests selected by the SAME verified recording media clock; no claim of physical AV synchronization, laptop hardware FPS or independent articulation quality.'},null,2)+'\n');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
