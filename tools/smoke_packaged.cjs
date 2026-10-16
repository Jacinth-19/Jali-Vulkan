// Frozen Windows runtime check: the app itself needs no Python/Node/gh on PATH.
const fs=require('node:fs'),{chromium}=require('playwright-core');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--enable-unsafe-swiftshader']}),page=await browser.newPage();const errors=[],external=[],origin=new URL(process.argv[2]).origin;
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url())&&!r.url().startsWith(origin+'/'))external.push(r.url());});
 try{
  await page.goto(process.argv[2]);await page.waitForFunction(()=>window.JaliHeadDemo?.getState().ready&&!document.querySelector('#generate').disabled,null,{timeout:60000});
  await page.locator('#text').fill('Hello from the portable local face studio. Please bring my blue paper bag.');await page.locator('#generate').click();
  await page.waitForFunction(()=>JaliStudio.getState().busy);await page.waitForFunction(()=>!JaliStudio.getState().busy,null,{timeout:200000});
  const first=await page.evaluate(()=>JaliStudio.getState());if(!first.verified||first.phase!=='ready')throw Error('Frozen worker failed: '+await page.locator('#error').textContent());
  await page.locator('#stop').click();await page.locator('#batch').check();await page.locator('#text').fill('Mama brought my blue paper bag. Five vivid voices move very fast.');await page.locator('#generate').click();
  await page.waitForFunction(()=>JaliStudio.getState().busy);await page.waitForFunction(()=>!JaliStudio.getState().busy,null,{timeout:240000});
  const state=await page.evaluate(()=>JaliStudio.getState());if(!state.verified||state.phase!=='ready'||state.streamStats.chunks.length!==2||errors.length||external.length)throw Error('Frozen batched playback failed: '+JSON.stringify({state,errors,external}));
  fs.writeFileSync(process.argv[3],JSON.stringify({passed:true,first_session:first.selectedId,combined_session:state.selectedId,stream:state.streamStats,errors,external,limits:'Hosted Windows portable runtime test; not target laptop or unsigned-warning UX acceptance'},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
