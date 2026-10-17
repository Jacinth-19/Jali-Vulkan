// Run against a fixture server OR the actual frozen app; receipts state which.
const fs=require('node:fs'),path=require('node:path');
(async()=>{
 const base=process.argv[2].replace(/\/$/,''),out=process.argv[3]||'artifacts/character-selector-proof/browser.json';
 const browser=await require('./test_browser.cjs').launch(),page=await browser.newPage({viewport:{width:1400,height:1200}}),errors=[],external=[],origin=new URL(base).origin;
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url())&&new URL(r.url()).origin!==origin)external.push(r.url());});
 const ready=()=>page.waitForFunction(()=>window.JaliWorkspace&&JaliHeadDemo.getState().ready&&!document.querySelector('#generate').disabled,null,{timeout:90000});
 const config=async name=>(await page.request.get(`${base}/characters/${name}/api/config`)).json();
 try{
  await page.goto(base+'/characters/male/?preset=low&lod=low');await ready();
  const male=await config('male'),female=await config('female'),releases=[];
  if(male.rig.model_sha256===female.rig.model_sha256)throw Error('Selector contains duplicate meshes');
  if(!(await page.locator('#prepared-character-panel').isVisible()))throw Error('Prepared-character selector is hidden');
  const model=await page.evaluate(()=>JaliHeadDemo.getDiagnostics().renderAsset);
  if(model.lod!=='low')throw Error('Scoped low LOD fetch failed');
  await page.evaluate(()=>JaliCreative.getCharacterSettings());
  await page.selectOption('#prepared-character','female');await page.waitForURL('**/characters/female/**');await ready();
  releases.push(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('jali.character.release'))));
  if(releases[0].model!==male.rig.model_sha256||releases[0].readyAfterUnload!==false)throw Error('Old male renderer was not explicitly released');
  const femaleRig=await page.evaluate(()=>JALI_HEAD_DATA.rig);
  if(femaleRig.model_sha256!==female.rig.model_sha256)throw Error('Female selector silently retained male');
  await page.evaluate(()=>JaliStudio.generate('Mama brought my blue paper bag.'));
  const femaleState=await page.evaluate(()=>JaliStudio.getState());
  if(!femaleState.verified)throw Error('Female recording failed');
  await page.selectOption('#prepared-character','male');await page.waitForURL('**/characters/male/**');await ready();
  releases.push(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('jali.character.release'))));
  if(releases[1].model!==female.rig.model_sha256||releases[1].readyAfterUnload!==false)throw Error('Old female renderer was not released');
  const cross=await page.request.get(base+'/characters/male/api/jobs/'+femaleState.selectedId);
  if(cross.status()!==404)throw Error('A female recording leaked into male session lookup');
  await page.evaluate(()=>JaliStudio.generate('Five vivid voices move very fast.'));
  const maleState=await page.evaluate(()=>JaliStudio.getState());
  if(!maleState.verified||await page.evaluate(()=>JALI_HEAD_DATA.rig.model_sha256)!==male.rig.model_sha256)throw Error('Male recording or current mesh failed');
  if(errors.length||external.length)throw Error(JSON.stringify({errors,external}));
  fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify({passed:true,male_rig:male.rig,female_rig:female.rig,release_markers:releases,scoped_low_lod:true,rig_isolated_recordings:true,verified_female_session:femaleState.selectedId,verified_male_session:maleState.selectedId,errors,external,limits:'One loaded character per document. Not a total-memory measurement across tabs, physical AV or perceptual acceptance. Speech versus explicit non-speech fixture is specified by the invoking receipt.'},null,2));
  console.log('Male/female selection, explicit unload, scoped LOD and both rig-bound recordings passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
