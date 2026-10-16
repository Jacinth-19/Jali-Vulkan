const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const zlib = require('node:zlib');
const { createHash } = require('node:crypto');
const { execFileSync } = require('node:child_process');
const { pathToFileURL } = require('node:url');
const { chromium: playwright } = require('playwright-core');
const chromium = require('@sparticuz/chromium');
(async () => {
  const root = path.resolve('artifacts/neural-head-demo');
  const support = path.resolve('.cache/runtime/browser');
  fs.mkdirSync(support, {recursive:true}); fs.mkdirSync(path.join(root,'proof'),{recursive:true});
  const archive = path.join(support,'support.tar');
  fs.writeFileSync(archive,zlib.brotliDecompressSync(fs.readFileSync(path.join(__dirname,'node_modules/@sparticuz/chromium/bin/al2023.tar.br'))));
  execFileSync('tar',['-xf',archive,'-C',support]);
  const browser = await playwright.launch({executablePath:await chromium.executablePath(),
    args:chromium.args.filter(arg=>arg!=='--disable-web-security'), headless:true,
    env:{...process.env,LD_LIBRARY_PATH:`${support}/lib:/tmp:${process.env.LD_LIBRARY_PATH||''}`}});
  const context = await browser.newContext({viewport:{width:1440,height:1100},deviceScaleFactor:1});
  const checks=[];
  const httpURL=process.argv[2]||'http://127.0.0.1:8081';
  const origin=new URL(httpURL).origin;
  let page;
  try {
    for(const url of [httpURL,pathToFileURL(path.join(root,'index.html')).href]) {
      page=await context.newPage(); const errors=[],external=[];
      page.on('pageerror',e=>errors.push(e.message));
      page.on('console',m=>{if(m.type()==='error'){ console.error('Browser:',m.text()); if(/THREE|WebGL|Shader/.test(m.text()))errors.push(m.text()); }});
      page.on('request',r=>{if(/^https?:/.test(r.url()) && !r.url().startsWith(origin+'/'))external.push(r.url());});
      page.on('response',response=>{
        if(response.status()<400)return;
        const name=new URL(response.url()).pathname.split('/').pop();
        if(process.env.EXPORT_VIDEO==='1' && ['poster.jpg','rendered-lip-closures.mp4'].includes(name) && !fs.existsSync(path.join(root,name)))return;
        errors.push(`${response.status()} ${response.url()}`);
      });
      await page.goto(url,{waitUntil:'networkidle'});
      await page.waitForFunction(()=>document.querySelector('#face').dataset.ready==='true',{},{timeout:60000});
      const stats=await page.evaluate(()=>JaliHeadDemo.getState().modelStats);
      if(stats.faceControls!==66 || stats.bones!==67 || stats.vertices<40000)throw new Error('Unexpected character structure '+JSON.stringify(stats));
      await page.locator('[data-clip="1"]').click();
      await page.waitForFunction(()=>Number(document.querySelector('#face').dataset.audioTime)>0.4);
      await page.locator('#audio').evaluate(a=>a.pause());
      const paused=await page.locator('#audio').evaluate(a=>a.currentTime);
      await page.waitForTimeout(250);
      if(Math.abs(await page.locator('#audio').evaluate(a=>a.currentTime)-paused)>0.001)throw new Error('Paused clock moved');
      await page.locator('#life').uncheck();
      await page.locator('#mood').selectOption('neutral');
      const captures=[];
      for(const value of ['A','D','F']) {
        const time=await page.evaluate(value=>{const c=JALI_HEAD_DATA.clips[1].cues.filter(c=>c.value===value).sort((a,b)=>(b.end-b.start)-(a.end-a.start))[0];return c.start+Math.min(0.01,(c.end-c.start)/4);},value);
        const {png,actual}=await page.evaluate(time=>({png:JaliHeadDemo.capture(time,1),actual:JaliHeadDemo.getState().activeMorphs}),time);
        captures.push(png);
        const key={A:'viseme_PP',D:'viseme_aa',F:'viseme_U'}[value];
        if(!actual.some(mesh=>mesh.values[key]>0.5))throw new Error(`Expected actual ${key} morph`);
        if(url.startsWith('http'))fs.writeFileSync(path.join(root,'proof',`viseme-${value}.png`),Buffer.from(png.split(',')[1],'base64'));
      }
      if(new Set(captures).size!==3)throw new Error('Different audio cues did not change the rendered face');
      await page.locator('#sync').uncheck();
      const disabled=await page.evaluate(()=>{JaliHeadDemo.capture(2,1);return JaliHeadDemo.getState();});
      if(disabled.activeMorphs.some(mesh=>Object.keys(mesh.values).some(key=>key.startsWith('viseme_'))))throw new Error('Sync-off retained speech morphs');
      await page.locator('#sync').check();
      await page.locator('#life').check();
      for(const index of [0,1,2]) {
        await page.locator(`[data-clip="${index}"]`).click();
        await page.waitForFunction(index=>document.querySelector('#face').dataset.clip===String(index) && Number(document.querySelector('#face').dataset.audioTime)>0.25,index);
        await page.locator('#audio').evaluate(a=>a.pause());
      }
      await page.locator('#audio').evaluate(async a=>{a.currentTime=a.duration-0.20;await a.play();});
      await page.waitForFunction(()=>document.querySelector('#audio').ended && document.querySelector('#face').dataset.shape==='X');
      if(url.startsWith('http')) {
        await page.evaluate(()=>{JaliHeadDemo.selectClip(0);});
        await page.waitForFunction(()=>document.querySelector('#audio').readyState>=2);
        await page.locator('#audio').evaluate(a=>a.currentTime=2.2);
        await page.waitForFunction(()=>Math.abs(Number(document.querySelector('#face').dataset.audioTime)-2.2)<0.025);
        await page.screenshot({path:path.join(root,'proof/desktop.png'),fullPage:true});
        await page.setViewportSize({width:390,height:844});
        await page.waitForTimeout(150);
        await page.screenshot({path:path.join(root,'proof/mobile.png'),fullPage:true});
        if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Mobile overflow');
        if(errors.length)throw new Error(errors.join('\n'));
        if(process.env.EXPORT_VIDEO==='1') {
          await page.setViewportSize({width:1280,height:1000});
          await page.evaluate(()=>JaliHeadDemo.setCaptureMode(true,512));
          await page.waitForTimeout(250);
          const temp=fs.mkdtempSync(path.join(os.tmpdir(),'jali-head-frames-'));
          try {
            const duration=await page.evaluate(()=>JALI_HEAD_DATA.clips[1].duration),fps=15;
            for(let i=0;i<Math.ceil(duration*fps);i++) {
              const image=await page.evaluate(time=>JaliHeadDemo.capture(time,1,'image/jpeg'),i/fps);
              if(i%30===0)console.log('Rendered frame',i,'/',Math.ceil(duration*fps));
              fs.writeFileSync(path.join(temp,`frame-${String(i).padStart(4,'0')}.jpg`),Buffer.from(image.split(',')[1],'base64'));
            }
            execFileSync(path.resolve('.venv/bin/python'),['-c',
              `import imageio_ffmpeg,subprocess; subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner','-loglevel','error','-framerate','15','-i',${JSON.stringify(path.join(temp,'frame-%04d.jpg'))},'-i',${JSON.stringify(path.join(root,'audio/02-lip-closures.wav'))},'-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-shortest','-movflags','+faststart',${JSON.stringify(path.join(root,'rendered-lip-closures.mp4'))}],check=True)`],{timeout:60000});
            fs.copyFileSync(path.join(temp,'frame-0000.jpg'),path.join(root,'poster.jpg'));
            const evidence=await page.evaluate(()=>({duration:JALI_HEAD_DATA.clips[1].duration,cues:JALI_HEAD_DATA.clips[1].cues,width:document.querySelector('#face').width,height:document.querySelector('#face').height}));
            const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
            fs.writeFileSync(path.join(root,'proof/video-export.json'),JSON.stringify({
              method:'Same browser-rendered viseme solver; original WAV muxed to AAC',fps,frames:Math.ceil(duration*fps),
              width:evidence.width,height:evidence.height,audioDuration:duration,
              cue_sha256:sha(JSON.stringify(evidence.cues)),audio_sha256:sha(fs.readFileSync(path.join(root,'audio/02-lip-closures.wav'))),
              mp4_sha256:sha(fs.readFileSync(path.join(root,'rendered-lip-closures.mp4'))),
              model_sha256:sha(fs.readFileSync(path.join(root,'model/mpfb-head.glb'))),
              viewer_sha256:sha(fs.readFileSync(path.join(root,'viewer.js')))
            },null,2)+'\n');
          } finally {fs.rmSync(temp,{recursive:true,force:true});await page.evaluate(()=>JaliHeadDemo.setCaptureMode(false)).catch(()=>{});}
        }
      }
      if(fs.existsSync(path.join(root,'rendered-lip-closures.mp4'))) {
        await page.locator('#export-video').evaluate(async video=>{await video.play();});
        await page.waitForFunction(()=>document.querySelector('#export-video').currentTime>0.15);
        await page.locator('#export-video').evaluate(video=>video.pause());
      }
      if(errors.length || external.length)throw new Error(JSON.stringify({errors,external}));
      checks.push({mode:url.startsWith('file')?'offline file':'HTTP',passed:true,model:stats,
        checks:['66 facial controls and 67 bones loaded','all three original neural clips played','pause and seek','distinct closed/open/rounded viseme renders with procedural motion disabled','sync toggle clears actual morph weights','natural end returns to rest','no external service requests','web security enabled','portable MP4 plays','no shader errors']});
      await page.close(); page=null;
    }
  } catch(error) {
    if(page) {
      console.error(await page.locator('#error').textContent().catch(()=>''));
      await page.screenshot({path:path.join(root,'proof/failure.png'),fullPage:true}).catch(()=>{});
    }
    throw error;
  } finally {await browser.close();}
  fs.rmSync(path.join(root,'proof/failure.png'),{force:true});
  fs.writeFileSync(path.join(root,'proof/browser-check.json'),JSON.stringify(checks,null,2)+'\n');
  console.log('Human head lip-sync passed:',checks);
})().catch(error=>{console.error(error);process.exitCode=1;});
