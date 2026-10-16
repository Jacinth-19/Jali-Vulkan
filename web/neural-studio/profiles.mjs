import {articulation} from '../neural-head/articulation.mjs';
export function profileBook(value,rig){
 if(!value||value.schema!=='jali-character-profiles-v1'||value.rig!==rig||Object.keys(value).some(k=>!['schema','rig','profiles'].includes(k))||!Array.isArray(value.profiles)||value.profiles.length>20)throw Error('Invalid profile book or different character rig');
 const names=new Set();return {schema:value.schema,rig,profiles:value.profiles.map(p=>{
  if(!p||p.calibration==null||Object.keys(p).some(k=>!['name','calibration'].includes(k))||typeof p.name!=='string'||p.name.length<1||p.name.length>48||p.name!==p.name.trim()||/[\x00-\x1f\x7f]/.test(p.name)||names.has(p.name))throw Error('Use unique profile names (1–48 characters)');
  names.add(p.name);return {name:p.name,calibration:articulation(p.calibration)};
 })};
}
export function saveProfile(book,name,calibration){
 const profiles=book.profiles.filter(p=>p.name!==name);profiles.push({name,calibration});return profileBook({...book,profiles},book.rig);
}
