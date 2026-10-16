import {creativeSettings,EXPRESSIONS} from '../neural-head/creative.mjs';
import {appearanceSettings} from '../neural-head/appearance.mjs';
import {profileBook,saveProfile} from './profiles.mjs';
import {animationTimeline,timelineCSV} from './export.mjs';
import {recordingController} from './recording.mjs';
export function installCreativeControls(api){
 const $=id=>document.getElementById(id),rig=api.rig.model_sha256,key='jali.profiles.'+rig,urls=new Map();
 let book={schema:'jali-character-profiles-v1',rig,profiles:[]},creative=creativeSettings({seed:parseInt(rig.slice(0,4),16)}),previousGaze=$('gaze').value;
 const report=message=>{$('creative-status').textContent=message;};
 function guard(fn){return async()=>{try{await fn();}catch(e){report(e.message);}};}
 function offer(name,blob,click=false){if(urls.has(name))URL.revokeObjectURL(urls.get(name));const url=URL.createObjectURL(blob);urls.set(name,url);let a=[...$('export-links').children].find(a=>a.download===name);if(!a){a=document.createElement('a');a.download=name;a.textContent=name;$('export-links').append(a);}a.href=url;if(click)a.click();}
 const json=(name,value,click=true)=>offer(name,new Blob([JSON.stringify(value,null,2)],{type:'application/json'}),click);
 window.addEventListener('beforeunload',()=>{for(const url of urls.values())URL.revokeObjectURL(url);});
 function refreshProfiles(){const select=$('saved-profile');select.replaceChildren();for(const p of book.profiles){const o=document.createElement('option');o.value=p.name;o.textContent=p.name;select.append(o);}}
 function store(next){localStorage.setItem(key,JSON.stringify(next));book=next;refreshProfiles();}
 try{const saved=localStorage.getItem(key);if(saved)book=profileBook(JSON.parse(saved),rig);}catch(e){report('Stored profiles could not be loaded: '+e.message);}refreshProfiles();
 $('profile-save').onclick=guard(()=>{store(saveProfile(book,$('profile-name').value.trim(),api.getCalibration()));report('Saved calibration for this character.');});
 $('profile-load').onclick=guard(()=>{const p=book.profiles.find(p=>p.name===$('saved-profile').value);if(!p)throw Error('Choose a saved profile');api.setCalibration(p.calibration);$('profile-name').value=p.name;report('Loaded '+p.name);});
 $('profile-delete').onclick=guard(()=>{store({...book,profiles:book.profiles.filter(p=>p.name!==$('saved-profile').value)});report('Named profile removed; current sliders are unchanged.');});
 $('profile-export').onclick=()=>json('character-profiles.json',book);
 $('profile-import').onchange=guard(async()=>{const f=$('profile-import').files[0];if(!f)return;if(f.size>65536)throw Error('Profile file exceeds 64 KiB');const next=profileBook(JSON.parse(await f.text()),rig);store(next);report('Imported profile book for this character.');$('profile-import').value='';});
 const inputs=['natural','intensity','contact','head','blink','blinkRate','gazeEase'];
 function readCreative(){const p={...creative};for(const k of inputs)p[k]=k==='natural'?$('creative-'+k).checked:Number($('creative-'+k).value);p.sequence=[...$('expression-events').children].map(row=>({start:Number(row.querySelector('[data-start]').value),end:Number(row.querySelector('[data-end]').value),expression:row.querySelector('select').value,intensity:Number(row.querySelector('[data-intensity]').value),fade:Number(row.querySelector('[data-fade]').value)}));return creativeSettings(p);}
 function applyCreative(){creative=readCreative();api.setCreative(creative);}
 for(const k of inputs)$('creative-'+k).addEventListener('input',guard(applyCreative));
 $('gaze').addEventListener('change',guard(()=>{creative={...creative,gazeFrom:previousGaze,gazeStart:window.JaliHeadDemo.getState().sessionId?Math.min(60,$('audio').currentTime+(window.JaliHeadDemo.getState().streamOffset||0)):window.JaliHeadDemo.getState().idleTime};previousGaze=$('gaze').value;applyCreative();}));
 function addEvent(e={start:0,end:2,expression:'warm',intensity:1,fade:.2}){
  if($('expression-events').children.length>=32)throw Error('At most 32 expression events');
  const row=document.createElement('div');row.className='expression-event';
  for(const [k,label,step] of [['start','Start s',.1],['end','End s',.1]]){const l=document.createElement('label');l.textContent=label;const input=document.createElement('input');input.type='number';input.min=0;input.max=60;input.step=step;input.value=e[k];input.dataset[k]='';l.append(input);row.append(l);}
  const select=document.createElement('select');select.setAttribute('aria-label','Timed manual expression');for(const v of EXPRESSIONS){const o=document.createElement('option');o.value=v;o.textContent=v;select.append(o);}select.value=e.expression;row.append(select);
  for(const [k,label,max] of [['intensity','Strength',1],['fade','Fade s',2]]){const l=document.createElement('label');l.textContent=label;const input=document.createElement('input');input.type='number';input.min=0;input.max=max;input.step=.05;input.value=e[k];input.dataset[k]='';l.append(input);row.append(l);}
  const remove=document.createElement('button');remove.type='button';remove.textContent='Remove';remove.className='secondary';remove.onclick=guard(()=>{row.remove();applyCreative();});row.append(remove);row.addEventListener('change',guard(applyCreative));$('expression-events').append(row);
 }
 $('expression-add').onclick=guard(()=>{addEvent();applyCreative();});
 $('sequence-export').onclick=guard(()=>json('manual-performance.json',{schema:'jali-manual-performance-v1',rig,creative:readCreative(),base:{mood:$('mood').value,gaze:$('gaze').value,life:$('life').checked}}));
 $('sequence-import').onchange=guard(async()=>{const f=$('sequence-import').files[0];if(!f)return;if(f.size>65536)throw Error('Performance file exceeds 64 KiB');const v=JSON.parse(await f.text());if(v.schema!=='jali-manual-performance-v1'||v.rig!==rig)throw Error('Performance belongs to a different character');const p=creativeSettings(v.creative),base=v.base;if(!base||Object.keys(base).some(k=>!['mood','gaze','life'].includes(k))||!EXPRESSIONS.includes(base.mood)||!['forward','left','right','down'].includes(base.gaze)||typeof base.life!=='boolean')throw Error('Invalid manual base controls');$('mood').value=base.mood;$('gaze').value=base.gaze;$('life').checked=base.life;previousGaze=base.gaze;$('expression-events').replaceChildren();creative=p;for(const k of inputs){if(k==='natural')$('creative-'+k).checked=p[k];else $('creative-'+k).value=p[k];}for(const e of p.sequence)addEvent(e);applyCreative();report('Manual performance imported.');$('sequence-import').value='';});
 const appearanceKeys=['lighting','background','camera','exposure','skin','eyes','fxaa'];
 for(const k of appearanceKeys)$('look-'+k).addEventListener('input',guard(()=>{const p={};for(const k of appearanceKeys)p[k]=k==='fxaa'?$('look-'+k).checked:['exposure','skin','eyes'].includes(k)?Number($('look-'+k).value):$('look-'+k).value;window.JaliHeadDemo.setAppearance(appearanceSettings(p));report('WebGL appearance updated.');}));
 function clip(){if(api.isBusy()||$('renderer').value!=='webgl'&&recorder.active)throw Error('Finish generation/recording first');const c=api.getClip();if(!c)throw Error('Select a completed verified recording first');return c;}
 function timeline(){if(recorder.active)throw Error('Finish recording first');return {...animationTimeline(clip(),{fps:Number($('export-fps').value),calibration:api.getCalibration(),creative:readCreative(),mood:$('mood').value,gaze:$('gaze').value,life:$('life').checked,sync:$('sync').checked,trim:Number($('trim').value)/1000}),render_asset:window.JaliHeadDemo.getState().renderAsset};}
 $('export-json').onclick=guard(()=>json('facial-animation.json',timeline()));
 $('export-csv').onclick=guard(()=>offer('facial-weights.csv',new Blob([timelineCSV(timeline())],{type:'text/csv'}),true));
 const exportSettings=()=>({fps:Number($('export-fps').value),resolution:api.getQuality().resolution,calibration:api.getCalibration(),creative:readCreative(),mood:$('mood').value,gaze:$('gaze').value,life:$('life').checked,sync:$('sync').checked,trim:Number($('trim').value)/1000,appearance:window.JaliHeadDemo.getState().appearance});
 const recorder=recordingController({audio:$('audio'),canvas:$('face'),head:window.JaliHeadDemo,getClip:clip,getSettings:exportSettings,lock:value=>{api.lock(value);$('record-start').disabled=value;$('record-stop').disabled=!value;document.querySelectorAll('[data-creative-panel] input,[data-creative-panel] select,[data-creative-panel] button').forEach(n=>{if(!['record-stop'].includes(n.id))n.disabled=value;});},offer,clear:()=>{for(const name of ['performance.webm','recorded-frames.json']){if(urls.has(name))URL.revokeObjectURL(urls.get(name));urls.delete(name);[...$('export-links').children].find(a=>a.download===name)?.remove();}},status:report});
 $('record-start').onclick=guard(async()=>{if($('renderer').value!=='webgl')throw Error('Video capture uses WebGL; select it explicitly. Native still supports weight timeline exports.');if(api.isBusy())throw Error('Finish generation first');if($('observe').disabled)throw Error('Finish the playback observation first');await recorder.start();});
 $('record-stop').onclick=()=>recorder.stop();
 function appearanceAvailability(){const native=$('renderer').value==='native';$('appearance-controls').disabled=native;$('appearance-note').textContent=native?'Native uses its fixed camera/material/light pipeline. These appearance controls and video capture are WebGL-only.':'WebGL appearance settings; MSAA is enabled, optional FXAA adds another anti-aliasing pass. Native retains its own fixed appearance.';}
 $('renderer').addEventListener('change',appearanceAvailability);appearanceAvailability();
 // Defaults reproduce the original neutral/legacy animation; advanced motion is opt-in.
 api.setCreative(creative);
 return {getSettings:()=>creative,recording:recorder,
  getCharacterSettings:()=>({calibration:api.getCalibration(),creative:readCreative(),appearance:window.JaliHeadDemo.getState().appearance,mood:$('mood').value,gaze:$('gaze').value,life:$('life').checked}),
  applyCharacterSettings:s=>{const p=creativeSettings(s.creative);if(!EXPRESSIONS.includes(s.mood)||!['forward','left','right','down'].includes(s.gaze)||typeof s.life!=='boolean')throw Error('Invalid character performance');api.setCalibration(s.calibration);$('mood').value=s.mood;$('gaze').value=s.gaze;$('life').checked=s.life;previousGaze=s.gaze;creative=p;$('expression-events').replaceChildren();for(const k of inputs)if(k==='natural')$('creative-'+k).checked=p[k];else $('creative-'+k).value=p[k];for(const e of p.sequence)addEvent(e);applyCreative();if(s.appearance){const a=appearanceSettings(s.appearance);window.JaliHeadDemo.setAppearance(a);for(const k of appearanceKeys)if(k==='fxaa')$('look-'+k).checked=a[k];else $('look-'+k).value=a[k];}},
  setManualExpression:(style,intensity)=>{if(!EXPRESSIONS.includes(style)||typeof intensity!=='number'||!Number.isFinite(intensity)||intensity<0||intensity>1)throw Error('Invalid manual expression');$('mood').value=style;$('creative-intensity').value=intensity;applyCreative();}
 };

}
