import {articulation} from '../neural-head/articulation.mjs';
import {creativeSettings,EXPRESSIONS} from '../neural-head/creative.mjs';
import {appearanceSettings} from '../neural-head/appearance.mjs';
export const MAX_TURNS=128,MAX_TEXT=20000;
export const newId=()=>crypto.randomUUID().replaceAll('-','');
const id=v=>typeof v==='string'&&/^[a-f0-9]{32}$/.test(v);
export function castProfiles(value,voices){
 if(!Array.isArray(value)||!value.length||value.length>8)throw Error('Use 1–8 character profiles');const seen=new Set();
 return value.map(p=>{if(!p||Object.keys(p).some(k=>!['id','name','voice','speed','settings'].includes(k))||typeof p.id!=='string'||!/^[a-z][a-z0-9_-]{0,23}$/.test(p.id)||seen.has(p.id)||typeof p.name!=='string'||!p.name.trim()||p.name.length>48||/[\x00-\x1f\x7f]/.test(p.name)||!voices.includes(p.voice)||typeof p.speed!=='number'||!Number.isFinite(p.speed)||p.speed<.75||p.speed>1.25)throw Error('Invalid/duplicate character or unavailable voice');seen.add(p.id);
  const out=structuredClone(p);if(p.settings){const s=p.settings;if(Object.keys(s).some(k=>!['calibration','creative','mood','gaze','life','appearance'].includes(k))||!EXPRESSIONS.includes(s.mood)||!['forward','left','right','down'].includes(s.gaze)||typeof s.life!=='boolean')throw Error('Invalid character performance');out.settings={calibration:articulation(s.calibration),creative:creativeSettings(s.creative),mood:s.mood,gaze:s.gaze,life:s.life,appearance:s.appearance===null?null:appearanceSettings(s.appearance)};}return out;});
}
export function sentenceTurns(text,speaker,makeId=newId){
 if(typeof text!=='string'||text.length>MAX_TEXT||!text.trim()||/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(text))throw Error('Use nonblank dialogue up to 20000 characters');
 const turns=[];for(const paragraph of text.split(/\n+/)){for(const sentence of paragraph.trim().split(/(?<=[.!?])\s+/)){if(!sentence)continue;let chunk='';for(const word of sentence.split(/\s+/)){if(word.length>160)throw Error('A dialogue word exceeds 160 characters');if(chunk&&(chunk+' '+word).length>160){turns.push({id:makeId(),speaker,text:chunk,session:null});chunk='';}chunk+=(chunk?' ':'')+word;}if(chunk)turns.push({id:makeId(),speaker,text:chunk,session:null});}}
 if(turns.length>MAX_TURNS)throw Error('Dialogue exceeds 128 sentence turns');return turns;
}
export function conversationDocument(value,voices){
 if(!value||Object.keys(value).some(k=>!['schema','id','name','cast','turns'].includes(k))||value.schema!=='jali-conversation-v1'||!id(value.id)||typeof value.name!=='string'||!value.name.trim()||value.name.length>80||/[\x00-\x1f\x7f]/.test(value.name)||!Array.isArray(value.turns)||!value.turns.length||value.turns.length>MAX_TURNS)throw Error('Invalid conversation');
 const cast=castProfiles(value.cast,voices),names=new Set(cast.map(p=>p.id)),seen=new Set();let total=0;
 for(const t of value.turns){if(!t||Object.keys(t).some(k=>!['id','speaker','text','session'].includes(k))||!id(t.id)||seen.has(t.id)||!names.has(t.speaker)||typeof t.text!=='string'||!t.text.trim()||t.text.length>160||/[\x00-\x1f\x7f]/.test(t.text)||t.session!==null&&!id(t.session))throw Error('Invalid dialogue turn');seen.add(t.id);total+=t.text.length;}
 if(total>MAX_TEXT)throw Error('Dialogue exceeds 20000 characters');return structuredClone({...value,cast});
}
