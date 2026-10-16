// Actual stock-voice inference through the one-worker saved-dialogue UI.
const fs=require('node:fs'),path=require('node:path'),{createHash}=require('node:crypto');
exports.checkVoices=async(page,context,base,proof)=>{
 const installed=await(await context.request.get(base+'/api/config')).json(),identities={af_bella:'f69d836209b78eb8c66e75e3cda491e26ea838a3674257e9d4e5703cbaf55c8b',am_michael:'1d1f21dd8da39c30705cd4c75d039d265e9bc4a2a93ed09bc9e1b1225eb95ba1'},selected=Object.keys(identities).filter(v=>installed.voices.includes(v)),voices=[];
 if(process.env.GITHUB_ACTIONS==='true'&&selected.length!==2)throw Error('Hosted proof requires both explicitly prepared optional voices');
 if(await page.evaluate(()=>JaliWorkspace.getState().doc.turns.length))throw Error('Voice proof needs a fresh conversation');
 await page.locator('summary').filter({hasText:'Character profiles & voices'}).evaluate(n=>n.parentElement.open=true);
 for(const voice of selected){
  await page.fill('#cast-id',voice);await page.fill('#cast-name',voice);await page.selectOption('#cast-voice',voice);await page.fill('#cast-speed','1');await page.click('#cast-add');await page.waitForFunction(v=>Array.from(document.querySelector('#speaker').options).some(o=>o.value===v),voice);
  await page.selectOption('#speaker',voice);await page.fill('#dialogue-text','Please bring the blue bag.');await page.click('#dialogue-add');
 }
 if(selected.length){await page.click('#dialogue-play');await page.waitForFunction(()=>JaliWorkspace.getState().index===JaliWorkspace.getState().doc.turns.length&&!JaliWorkspace.getState().inflight,null,{timeout:180000});}
 const dialogue=await page.evaluate(()=>JaliWorkspace.getState());
 for(const turn of dialogue.doc.turns){
  const clip=await(await context.request.get(`${base}/sessions/${turn.session}/manifest.json`)).json(),voice=turn.speaker,expected=identities[voice],wave=await(await context.request.get(base+clip.file)).body();
  if(createHash('sha256').update(wave).digest('hex')!==clip.audio.sha256||clip.analysis.audio_sha256!==clip.audio.sha256||clip.text!==turn.text||clip.tts.providers.join()!=='CPUExecutionProvider')throw Error('Dialogue WAV/text/CPU binding mismatch');
  if(clip.tts.stock_voice!==voice||clip.tts.voice_sha256!==expected||clip.speaker.voice!==voice||clip.speaker.speed!==1)throw Error('Character voice identity mismatch');
  voices.push({voice,voice_sha256:expected,audio_sha256:clip.audio.sha256,duration:clip.duration,tts:clip.tts,total_seconds:clip.total_seconds});
 }
 if(voices.length===2&&voices[0].audio_sha256===voices[1].audio_sha256)throw Error('Different voices reused one WAV');
 const report={passed:true,fixture:false,voices,sequential_dialogue:voices.length===2,saved:dialogue.saved,shared_active_meshes:1,skipped:!voices.length,limits:'Actual new stock-voice sessions; not voice-00, cloned identity, subjective quality or target-laptop performance'};
 fs.mkdirSync(proof,{recursive:true});fs.writeFileSync(path.join(proof,'character-voices.json'),JSON.stringify(report,null,2));console.log('Actual stock-voice dialogue checked',voices.length);return report;
};
if(require.main===module)(async()=>{const base=process.argv[2]||'http://127.0.0.1:8082',browser=await require('./test_browser.cjs').launch();try{const context=await browser.newContext(),page=await context.newPage();await page.goto(base+'?preset=low');await page.waitForFunction(()=>window.JaliWorkspace&&JaliHeadDemo.getState().ready&&!document.querySelector('#generate').disabled);await exports.checkVoices(page,context,base,path.resolve('artifacts/actual-voice-proof'));}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
