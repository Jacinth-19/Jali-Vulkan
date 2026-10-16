// Exercise the portable package over both HTTP and file:// without disabling web security.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),zlib=require('node:zlib');
const {pathToFileURL}=require('node:url'),{execFileSync}=require('node:child_process'),{createHash}=require('node:crypto');
const {chromium:playwright}=require('playwright-core'),chromium=require('@sparticuz/chromium');
(async()=>{
 const root=path.resolve('artifacts/Jali-Laptop-Playback-Checkpoint'),proof=path.resolve('artifacts/playback-checkpoint-proof');fs.mkdirSync(proof,{recursive:true});
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'package-manifest.json')));
 for(const [name,sha] of Object.entries(manifest.files))if(createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex')!==sha)throw Error('Package hash mismatch: '+name);
 const channel=process.env.JALI_BROWSER_CHANNEL;
 const support=path.resolve('.cache/runtime/browser');fs.mkdirSync(support,{recursive:true});
 if(!channel){
 const archive=path.join(support,'support.tar');fs.writeFileSync(archive,zlib.brotliDecompressSync(fs.readFileSync(path.join(__dirname,'node_modules/@sparticuz/chromium/bin/al2023.tar.br'))));execFileSync('tar',['-xf',archive,'-C',support]);
 }
 const allowed=new Set([...Object.keys(manifest.files),'package-manifest.json']);
 const server=http.createServer((req,res)=>{
   const name=new URL(req.url,'http://test').pathname.slice(1)||'index.html';
   if(name==='favicon.ico'){res.writeHead(204);return res.end();}
   if(!allowed.has(name)){res.writeHead(404);return res.end();}
   res.setHeader('Content-Type',name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':name.endsWith('.html')?'text/html':'text/plain');fs.createReadStream(path.join(root,name)).pipe(res);
 });
 await new Promise(resolve=>server.listen(0,'0.0.0.0',resolve));
 let browser;const results=[];
 try{
  for(const [mode,url] of [['HTTP',`http://127.0.0.1:${server.address().port}`],['file',pathToFileURL(path.join(root,'index.html')).href]]){
   browser=await playwright.launch(channel?{channel,headless:true,args:['--enable-unsafe-swiftshader']}:{executablePath:await chromium.executablePath(),headless:true,args:chromium.args.filter(a=>a!=='--disable-web-security'),env:{...process.env,LD_LIBRARY_PATH:`${support}/lib:/tmp:${process.env.LD_LIBRARY_PATH||''}`}});
   const context=await browser.newContext({viewport:{width:1360,height:1000},acceptDownloads:true}),page=await context.newPage(),errors=[],external=[];
   page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
   page.on('request',r=>{if(/^https?:/.test(r.url())&&(mode==='file'||!r.url().startsWith(url+'/')))external.push(r.url());});
   await page.goto(url,{waitUntil:'load'});await page.waitForFunction(()=>window.JaliCheckpoint&&JaliHeadDemo.getState().ready&&!document.querySelector('#measure').disabled,null,{timeout:60000});
   for(let i=0;i<manifest.corpus.length;i++){
    await page.locator(`button[data-clip="${i}"]`).click();
    const clip=await page.evaluate(i=>window.JALI_HEAD_DATA.clips[i],i);
    const bytes=Buffer.from(clip.file.split(',')[1],'base64');
    if(createHash('sha256').update(bytes).digest('hex')!==manifest.corpus[i].audio_sha256)throw Error('Embedded audio changed');
    await page.locator('#audio').evaluate(a=>a.play());await page.waitForFunction(()=>document.querySelector('#audio').currentTime>.15);
    if(await page.evaluate(()=>JaliHeadDemo.getState().sessionId)!==clip.id)throw Error('Wrong face/audio identity');
    await page.locator('#audio').evaluate(a=>a.pause());
   }
   await page.locator('button[data-clip="0"]').click();await page.locator('#notes').fill('Automated test note, not a human review.');await page.locator('#rating').selectOption('problem');
   await page.locator('button[data-clip="1"]').click();await page.locator('button[data-clip="0"]').click();
   if(await page.locator('#notes').inputValue()!=='Automated test note, not a human review.')throw Error('Notes lost on switch');
   await page.locator('#measure').click();await page.waitForFunction(()=>JaliCheckpoint.getRuns().length===1,null,{timeout:45000});
   const run=await page.evaluate(()=>JaliCheckpoint.getRuns()[0]);
   if(!run.valid_sample||run.reason!=='ended'||run.observed_render_fps===null||!run.diagnostics.webgl)throw Error('Playback measurement failed: '+JSON.stringify(run));
   await page.locator('#measure').click();await page.waitForFunction(()=>JaliCheckpoint.isMeasuring());await page.locator('#cancel').click();
   const cancelled=await page.evaluate(()=>JaliCheckpoint.getRuns()[1]);if(cancelled.valid_sample||cancelled.reason!=='cancelled')throw Error('Cancellation counted as success');
   await page.locator('#measure').click();await page.waitForFunction(()=>JaliCheckpoint.isMeasuring());await page.locator('#speed').selectOption('0.5');
   if((await page.evaluate(()=>JaliCheckpoint.getRuns()[2])).valid_sample)throw Error('Changed speed counted as success');
   const downloadPromise=page.waitForEvent('download');await page.locator('#download').click();const download=await downloadPromise;
   const filename=path.join(proof,`${mode}-automated-runner-report.json`);await download.saveAs(filename);const exported=JSON.parse(fs.readFileSync(filename));
   if(exported.quality_score!==null||exported.user_review_declared_complete||exported.corpus[0].rating!=='problem'||exported.runs.length!==3)throw Error('Export falsely completed quality review or lost data');
   await page.setViewportSize({width:390,height:844});await page.waitForTimeout(200);
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');
   await page.screenshot({path:path.join(proof,`${mode}-mobile.png`),fullPage:true});
   await page.setViewportSize({width:1360,height:1000});await page.screenshot({path:path.join(proof,`${mode}-desktop.png`),fullPage:true});
   if(errors.length||external.length)throw Error(JSON.stringify({errors,external}));
   results.push({mode,passed:true,web_security_enabled:true,errors,external,actual_playback:run,checks:['three embedded WAV hashes and actual playback','audio/face identity','notes survive clip switch','actual end completes measurement','cancel and speed change invalidate','downloaded report matches state','unreviewed cases remain pending','mobile layout']});
   await context.close();await browser.close();browser=null;console.log(mode,'portable checkpoint passed');
  }
  fs.writeFileSync(path.join(proof,'browser-check.json'),JSON.stringify({environment:`Automated ${process.platform} browser; NOT the user target laptop`,results},null,2)+'\n');
 }finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(e=>{console.error(e);process.exitCode=1;});
