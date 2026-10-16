// Real browser controls/transport test against EXPLICIT non-speech fixture server.
const fs=require('node:fs');
(async()=>{
 const browser=await require('./test_browser.cjs').launch();
 try{
 const page=await browser.newPage({viewport:{width:1400,height:1200}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.argv[2]||'http://127.0.0.1:8083');await page.waitForFunction(()=>window.JaliStudio&&!document.querySelector('#generate').disabled,null,{timeout:60000});
 for(const [preset,size,fps] of [['low',256,15],['high',768,60],['balanced',512,30]]){
  await page.selectOption('#quality-preset',preset);const q=await page.evaluate(()=>({settings:JaliStudio.getState().quality,canvas:JaliHeadDemo.getDiagnostics().canvas}));
  if(q.settings.fps!==fps||q.settings.resolution!==size||Math.max(q.canvas.width,q.canvas.height)>size)throw Error('Preset did not control actual framebuffer: '+JSON.stringify(q));
 }
 await page.selectOption('#quality-fps','24');if((await page.evaluate(()=>JaliStudio.getState().quality.fps))!==24)throw Error('Custom FPS failed');
 await page.selectOption('#quality-preset','balanced');
 await page.fill('#text','Fixture contacts.');await page.click('#generate');await page.waitForFunction(()=>!JaliStudio.getState().busy&&JaliStudio.getState().verified,null,{timeout:60000});
 await page.evaluate(()=>{document.querySelector('#audio').pause();document.querySelector('#audio').currentTime=.2;});
 await page.selectOption('#art-profile','baseline');const baseline=await page.evaluate(()=>{JaliHeadDemo.updateClock(.2);return JaliHeadDemo.getState().pose.viseme_PP;});
 await page.selectOption('#art-profile','clear');const clear=await page.evaluate(()=>{JaliHeadDemo.updateClock(.2);return JaliHeadDemo.getState().pose.viseme_PP;});if(Math.abs(baseline-.95)>1e-8||Math.abs(clear-.9975)>1e-8)throw Error('Closure calibration failed');
 // Isolate audio transport timing from software-GPU saturation. Actual renderer
 // presets/poses were checked above; this is not a combined AV/FPS benchmark.
 await page.evaluate(()=>JaliHeadDemo.setCaptureMode(true));await page.waitForTimeout(1500);
 await page.route('**/sessions/*/audio.wav',async route=>{await new Promise(r=>setTimeout(r,600));await route.continue();});
 await page.check('#batch');await page.fill('#text','One. Two. Three.');await page.click('#generate');await page.waitForFunction(()=>JaliStudio.getState().busy);await page.waitForFunction(()=>!JaliStudio.getState().busy,null,{timeout:60000});
 const state=await page.evaluate(()=>JaliStudio.getState());if(!state.verified||state.phase!=='ready'||state.streamStats.chunks.length!==3||state.streamStats.prebufferHits<1)throw Error('No verified prebuffer hit: '+JSON.stringify({...state,ui_error:await page.locator('#error').textContent()}));
 await page.uncheck('#prebuffer');await page.fill('#text','Without. Audio. Prebuffer.');await page.click('#generate');await page.waitForFunction(()=>JaliStudio.getState().busy);await page.waitForFunction(()=>!JaliStudio.getState().busy,null,{timeout:60000});
 const noBuffer=await page.evaluate(()=>JaliStudio.getState()),unbuffered=noBuffer.streamStats;
 if(noBuffer.phase!=='ready'||!noBuffer.verified||unbuffered.chunks.length!==3||unbuffered.prebufferHits!==0||unbuffered.downloadedAhead!==0||unbuffered.gapsMs.length!==2||state.streamStats.gapsMs.length!==2)throw Error('Controlled A/B transport did not complete both three-chunk arms');
 const average=a=>a.reduce((s,v)=>s+v,0)/a.length;
 if(average(unbuffered.gapsMs)<=average(state.streamStats.gapsMs)+50)throw Error('Controlled-delay prebuffer did not reduce handoff gaps (ms): '+JSON.stringify({buffered:state.streamStats.gapsMs,unbuffered:unbuffered.gapsMs}));
 await page.check('#prebuffer');await page.evaluate(()=>JaliHeadDemo.setCaptureMode(false));
 await page.fill('#text','Stop this. And this.');await page.click('#generate');await page.waitForFunction(()=>JaliStudio.getState().streamStats?.chunks.length===1);await page.click('#stop');await page.waitForFunction(()=>!JaliStudio.getState().busy,null,{timeout:30000});
 if(await page.evaluate(()=>JaliStudio.getState().selectedId!==null))throw Error('Stopped prefetch returned a stale session');
 await page.reload();await page.waitForFunction(()=>window.JaliStudio&&!document.querySelector('#generate').disabled);const saved=await page.evaluate(()=>JaliStudio.getState());if(saved.calibration.closure!==1.05||saved.quality.resolution!==512)throw Error('Settings did not persist');
 if(errors.length)throw Error(JSON.stringify(errors));
 fs.mkdirSync('artifacts/upgrade-proof',{recursive:true});fs.writeFileSync('artifacts/upgrade-proof/browser.json',JSON.stringify({passed:true,fixture:'Non-speech PCM + estimated-class fixture; not TTS or human quality approval',baseline,clear,stream:state.streamStats,unbuffered,controlled_wav_delay_ms:600,transport_timing_render_loop_suspended:true,presets:true,persistence:true,cancel_stale_guard:true,errors},null,2));console.log('Upgrade controls and actual prebuffer browser test passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
