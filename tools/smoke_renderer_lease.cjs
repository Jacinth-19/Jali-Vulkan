// Same-origin AND same browser context: unlike separate newPage() contexts,
// these pages really compete for one Web Lock. No fixture is called speech.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const base=process.argv[2].replace(/\/$/,''),out=process.argv[3]||'artifacts/renderer-lease/browser.json';
 const browser=await require('./test_browser.cjs').launch(),context=await browser.newContext(),anchor=await context.newPage(),errors=[];
 const page=async()=>{const p=await context.newPage();p.on('pageerror',e=>errors.push(e.message));return p;};
 const ready=p=>p.waitForFunction(()=>window.JaliHeadDemo?.getState().ready,null,{timeout:90000});
 try{
  const owner=await page();await owner.goto(base+'/characters/male/?preset=low');await ready(owner);
  const waiting=await page(),requests=[];waiting.on('request',r=>{if(r.url().includes('/model/'))requests.push(r.url());});await waiting.goto(base+'/characters/female/?preset=low');await waiting.waitForFunction(()=>window.JaliHeadDemo?.getState().leaseState==='waiting');
  await waiting.waitForTimeout(300);assert.equal(requests.length,0);assert.equal(await waiting.evaluate(()=>JaliHeadDemo.getDiagnostics().webgl),null);
  const cancelled=await page();await cancelled.goto(base+'/characters/male/?preset=low');await cancelled.waitForFunction(()=>window.JaliHeadDemo?.getState().leaseState==='waiting');await cancelled.evaluate(()=>JaliHeadDemo.unload());await cancelled.waitForFunction(()=>JaliHeadDemo.getState().leaseState==='cancelled');
  await owner.evaluate(()=>JaliHeadDemo.unload());await ready(waiting);assert.equal(requests.length,1);assert.equal(await cancelled.evaluate(()=>JaliHeadDemo.getState().ready),false);await cancelled.close();
  const releasedContextLost=await owner.evaluate(()=>JaliHeadDemo.getDiagnostics().webgl.contextLost);assert.equal(releasedContextLost,true);
  const successor=await page();await successor.goto(base+'/characters/male/?preset=low');await successor.waitForFunction(()=>window.JaliHeadDemo?.getState().leaseState==='waiting');await waiting.close();await ready(successor);assert.equal(await successor.evaluate(()=>JaliHeadDemo.getState().leaseState),'owned');
  await successor.evaluate(()=>JaliHeadDemo.unload());
  const partial=await page();let allow,seen;const blockedFetch=new Promise(r=>seen=r),allowFetch=new Promise(r=>allow=r);
  await partial.route('**/model/*.glb',async route=>{seen();await allowFetch;try{await route.continue();}catch{}});
  await partial.goto(base+'/characters/male/?preset=low');await blockedFetch;
  const afterCancel=await page();await afterCancel.goto(base+'/characters/female/?preset=low');await afterCancel.waitForFunction(()=>window.JaliHeadDemo?.getState().leaseState==='waiting');
  await partial.evaluate(()=>JaliHeadDemo.unload());allow();await ready(afterCancel);assert.equal(await partial.evaluate(()=>JaliHeadDemo.getState().ready),false);assert.equal(await partial.evaluate(()=>JaliHeadDemo.getDiagnostics().webgl.contextLost),true);
  assert.deepEqual(errors,[]);fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify({passed:true,same_origin_and_context:true,waiting_model_requests_before_release:0,waiting_webgl_context:null,cancelled_waiter_did_not_initialize:true,explicit_disposal_context_lost:releasedContextLost,close_releases_lock:true,initialization_cancel_disposes_before_release:true,errors,limits:'Exclusive renderer per origin/browser profile, not different origins/apps/profiles or a total-RAM measurement.'},null,2));console.log('Real same-context cross-tab renderer ownership passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
