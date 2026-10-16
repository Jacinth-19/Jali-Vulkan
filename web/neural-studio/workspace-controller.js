import {castProfiles,conversationDocument,sentenceTurns,newId} from './dialogue.mjs';
export function installWorkspace(api,config){
 const $=id=>document.getElementById(id),audio=$('audio'),key='jali.dialogue.'+config.rig.model_sha256;
 let doc={schema:'jali-conversation-v1',id:newId(),name:'Conversation',cast:config.cast,turns:[]},index=0,epoch=0,running=false,paused=false,saved=false,inflight=false;
 const consumer=newId();let lease=false,closed=false;
 const report=t=>{$('workspace-status').textContent=t;};
 const wait=ms=>new Promise(r=>setTimeout(r,ms));
 const post=(url,v)=>api.json(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(v)});
 const guard=fn=>async()=>{try{await fn();}catch(e){report(e.message);}};
 function persist(){try{localStorage.setItem(key,JSON.stringify({doc,index}));}catch{report('Browser draft storage is full; export or save the conversation.');}}
 function render(){
  $('dialogue-name').value=doc.name;for(const id of ['speaker','cast-select']){const select=$(id),old=select.value;select.replaceChildren();for(const p of doc.cast){const option=document.createElement('option');option.value=p.id;option.textContent=p.name+' · '+p.voice;select.append(option);}if(doc.cast.some(p=>p.id===old))select.value=old;}
  const list=$('dialogue-turns');list.replaceChildren();doc.turns.forEach((turn,i)=>{const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent=`${i+1}. ${doc.cast.find(p=>p.id===turn.speaker).name}: ${turn.text}`;button.setAttribute('aria-current',String(i===index));button.onclick=guard(()=>navigate(i));list.append(button);});
  $('dialogue-count').textContent=`${Math.min(index+1,doc.turns.length)} / ${doc.turns.length} · one active speaker/model worker`;
  persist();
 }
 async function syncCast(){doc.cast=castProfiles(doc.cast,config.voices);await post('/api/cast',doc.cast);}
 async function save(){if(!doc.turns.length)throw Error('Add dialogue first');doc.name=$('dialogue-name').value;doc=conversationDocument(doc,config.voices);await post('/api/conversations/save',doc);saved=true;persist();}
 async function refreshSaved(){const result=await api.json('/api/conversations');saved=result.conversations.some(c=>c.id===doc.id);$('saved-dialogues').replaceChildren();for(const c of result.conversations){const o=document.createElement('option');o.value=c.id;o.textContent=c.name;$('saved-dialogues').append(o);}}
 async function emit(type,data={}){if(lease)try{await post('/api/control/event',{consumer,type,data});}catch{lease=false;}}
 async function interrupt(){epoch++;running=false;paused=false;await api.interrupt();while(inflight)await wait(25);await emit('interrupted');report('Interrupted. The current sentence stays selected; partial generation is discarded.');}
 async function navigate(next){await interrupt();index=Math.max(0,Math.min(doc.turns.length-1,next));render();}
 async function start(){
  if(inflight){paused=false;if(api.state().verified)await api.play();return;}
  if(!doc.turns.length)throw Error('Add dialogue first');await refreshSaved();await syncCast();running=true;paused=false;inflight=true;const mine=++epoch;
  try{while(running&&mine===epoch&&index<doc.turns.length){const turn=doc.turns[index],profile=doc.cast.find(p=>p.id===turn.speaker);render();if(profile.settings)JaliCreative.applyCharacterSettings(profile.settings);report(`Preparing ${index+1}: ${profile.name} (${profile.voice})`);await emit('turn-start',{turn:turn.id,speaker:profile.id});
    let reused=false;
    if(saved&&turn.session!==null){try{const result=await post('/api/conversations/replay',{id:doc.id,turn:turn.id});await api.loadExisting(result.id);turn.session=result.id;reused=true;}catch(e){throw Error('Saved audio unavailable or mismatched; no silent regeneration: '+e.message);}}
    if(!reused)turn.session=(await api.generate(turn.text,profile)).id;
    if(mine!==epoch)break;
    // Pin each completed WAV before six-session eviction, never regenerate silently on hash/rig errors.
    try{await save();}catch(e){throw Error('Conversation could not be saved: '+e.message);}
    while(paused&&mine===epoch)await wait(100);if(mine!==epoch)break;
    if(!await api.play()){paused=true;report('Browser playback needs a Resume click.');}report(`Playing ${index+1}: ${profile.name}`);
    while(mine===epoch&&!audio.ended){if(audio.error)throw Error('Dialogue audio failed');await wait(75);}
    if(mine!==epoch)break;await emit('turn-done',{turn:turn.id,speaker:profile.id});index++;render();
   }
   if(mine===epoch){running=false;report('Conversation finished. Saved WAVs can replay without regeneration.');}
  }finally{inflight=false;if(mine===epoch)running=false;}
 }
 $('dialogue-add').onclick=guard(async()=>{if(inflight)throw Error('Interrupt before editing dialogue');const turns=sentenceTurns($('dialogue-text').value,$('speaker').value);const next={...doc,turns:[...doc.turns,...turns]};doc=conversationDocument(next,config.voices);render();report('Sentences queued; press Play dialogue.');});
 $('dialogue-play').onclick=guard(start);$('dialogue-pause').onclick=()=>{paused=true;audio.pause();report('Paused. Generation may finish, but the next sentence will not start.');};$('dialogue-resume').onclick=guard(async()=>{if(!inflight)return start();paused=false;if(api.state().verified)await api.play();});
 $('dialogue-interrupt').onclick=guard(interrupt);$('dialogue-prev').onclick=guard(()=>navigate(index-1));$('dialogue-next').onclick=guard(()=>navigate(index+1));
 $('dialogue-clear').onclick=guard(async()=>{await interrupt();doc={...doc,id:newId(),turns:[]};index=0;saved=false;render();});
 $('dialogue-save').onclick=guard(async()=>{await save();await refreshSaved();report('Conversation and available verified WAVs saved locally.');});
 $('dialogue-load').onclick=guard(async()=>{await interrupt();doc=conversationDocument(await api.json('/api/conversations/'+$('saved-dialogues').value),config.voices);saved=true;index=0;await syncCast();render();report('Saved conversation loaded; playback is not automatic.');});
 $('dialogue-delete').onclick=guard(async()=>{const id=$('saved-dialogues').value;if(!id)throw Error('Select a saved conversation');await post('/api/conversations/delete',{id});if(id===doc.id)saved=false;await refreshSaved();report('Saved conversation deleted.');});
 $('dialogue-export').onclick=guard(()=>{const value=conversationDocument({...doc,name:$('dialogue-name').value},config.voices),url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='conversation-script.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);report('Script/profile JSON exported; audio remains in the local saved conversation.');});
 $('dialogue-import').onchange=guard(async()=>{const f=$('dialogue-import').files[0];if(!f)return;if(f.size>262144)throw Error('Conversation JSON exceeds 256 KiB');const next=conversationDocument(JSON.parse(await f.text()),config.voices);await interrupt();doc={...next,id:newId(),turns:next.turns.map(t=>({...t,id:newId(),session:null}))};index=0;saved=false;await syncCast();render();});
 $('dialogue-name').onchange=()=>{doc.name=$('dialogue-name').value;persist();};
 $('cast-add').onclick=guard(async()=>{if(inflight||api.state().busy)throw Error('Interrupt before changing cast');const p={id:$('cast-id').value,name:$('cast-name').value,voice:$('cast-voice').value,speed:Number($('cast-speed').value),settings:JaliCreative.getCharacterSettings()},next=castProfiles([...doc.cast.filter(v=>v.id!==p.id),p],config.voices);if(saved&&doc.turns.some(t=>t.speaker===p.id)&&JSON.stringify(doc.cast.find(v=>v.id===p.id))!==JSON.stringify(p))throw Error('Saved turns use this character; create a new character ID instead');await post('/api/cast',next);doc.cast=next;render();report('Character saved with current calibration, expression and appearance; the prepared mesh is shared.');});
 $('cast-delete').onclick=guard(async()=>{if(inflight||api.state().busy)throw Error('Interrupt before editing cast');const id=$('cast-select').value;if(doc.turns.some(t=>t.speaker===id))throw Error('A dialogue turn still uses this character');const next=castProfiles(doc.cast.filter(p=>p.id!==id),config.voices);await post('/api/cast',next);doc.cast=next;render();});
 $('cast-select').onchange=()=>{const p=doc.cast.find(v=>v.id===$('cast-select').value);if(!p)return;$('cast-id').value=p.id;$('cast-name').value=p.name;$('cast-voice').value=p.voice;$('cast-speed').value=p.speed;};
 for(const voice of config.voices){const o=document.createElement('option');o.value=voice;o.textContent=voice;$('cast-voice').append(o);}
 $('lod-select').value=new URLSearchParams(location.search).get('lod')==='low'?'low':'full';$('lod-select').onchange=guard(async()=>{await interrupt();const url=new URL(location.href);url.searchParams.set('lod',$('lod-select').value);location.href=url;});
 $('unload-assets').onclick=guard(async()=>{await interrupt();JaliHeadDemo.unload();api.update();report('Character GPU/CPU geometry, textures and audio URLs released. Reload to restore.');});$('reload-assets').onclick=()=>location.reload();
 $('idle-throttle').onchange=()=>JaliHeadDemo.setIdleRate($('idle-throttle').checked?2:15);
 for(const event of ['play','pause','ended','error','loadedmetadata'])audio.addEventListener(event,()=>{if(event==='pause'&&inflight&&!audio.ended)paused=true;if(event==='play')paused=false;emit(event==='loadedmetadata'?'loaded':event,{session:audio.dataset.session||null,time:Math.min(60,audio.currentTime||0)});});
 try{const raw=localStorage.getItem(key);if(raw&&raw.length<=262144){const value=JSON.parse(raw);doc=conversationDocument(value.doc,config.voices);index=Math.min(doc.turns.length,Math.max(0,Number.isInteger(value.index)?value.index:0));}}catch(e){report('Draft unavailable: '+e.message);}
 syncCast().catch(e=>report(e.message));render();$('cast-select').dispatchEvent(new Event('change'));refreshSaved().catch(e=>report(e.message));
 $('integration-enable').disabled=!config.integration;$('integration-info').textContent=config.integration?'Opt-in broker ready. Enable this browser to accept local app commands.':'Disabled. Start with --bind 127.0.0.1 --integration-key-file <private-file> to enable.';
 async function poll(){while(!closed){if(config.integration&&$('integration-enable').checked){try{const result=await post('/api/control/poll',{consumer});lease=true;const c=result.command;if(c){try{const v=c.command;if(v.type==='submit'){const firstNew=doc.turns.length;if(!doc.cast.some(p=>p.id===v.speaker))throw Error('Unknown cast ID');doc=conversationDocument({...doc,turns:[...doc.turns,...sentenceTurns(v.text,v.speaker)]},config.voices);render();if(!inflight){index=firstNew;start().catch(e=>{report(e.message);emit('error',{message:e.message.slice(0,500)});});}}else if(v.type==='pause'){$('dialogue-pause').click();}else if(v.type==='resume'){start().catch(e=>{report(e.message);emit('error',{message:e.message.slice(0,500)});});}else if(v.type==='interrupt'){await interrupt();}else{JaliCreative.setManualExpression(v.expression,v.intensity);}await emit('command-done',{command:c.id});}catch(e){await emit('command-error',{command:c.id,message:e.message.slice(0,500)});}}}catch(e){lease=false;report(e.message);}}else lease=false;await wait(500);}}
 window.addEventListener('beforeunload',()=>{closed=true;persist();});poll();
 window.JaliWorkspace={getState:()=>({doc:structuredClone(doc),index,running,paused,inflight,saved}),interrupt,start};
}
