// Separate post-authoring diagnostic (shared triangle-intersection helper;
// NOT an independent implementation or human/perceptual reference):
// orthographic rays compare eye-vs-skin front depths on a fixed model-space grid.
// It does not reuse the author's per-vertex displacement or hide the eye mesh.
import {frontSurface,SEAL_NAMES} from './author_eye_clearance.mjs';
function posed(primitive,weights){
 const a=primitive.getAttribute('POSITION'),terms=primitive.listTargets().filter(t=>weights[t.getName()]).map(t=>[t.getAttribute('POSITION'),weights[t.getName()]]);
 return {getIndices:()=>primitive.getIndices(),getAttribute:()=>({getCount:()=>a.getCount(),getElement:(i,out)=>{const v=a.getElement(i,out);for(const [d,w] of terms){const delta=d.getElement(i,[]);for(let k=0;k<3;k++)v[k]+=w*delta[k];}return v;}})};
}
export function auditEyeClearance(doc,{step=.001}={}){
 if(!Number.isFinite(step)||step<.0005||step>.003)throw Error('Bounded coverage grid required');
 const root=doc.getRoot(),eyes=root.listNodes().find(n=>n.getName()==='Human.high-poly').getMesh().listPrimitives()[0],body=root.listNodes().find(n=>n.getName()==='Human').getMesh().listPrimitives()[0],a=eyes.getAttribute('POSITION'),v=Array.from({length:a.getCount()},(_,i)=>a.getElement(i,[])),eyeFront=frontSurface(eyes),samples=[];
 for(const sign of [-1,1]){
  const side=v.filter(p=>p[0]*sign>0),xs=side.map(p=>p[0]),ys=side.map(p=>p[1]);
  for(let x=Math.min(...xs)+step/2;x<Math.max(...xs);x+=step)for(let y=Math.min(...ys)+step/2;y<Math.max(...ys);y+=step){const z=eyeFront(x,y);if(Number.isFinite(z))samples.push({x,y,z,side:sign>0?'Left':'Right'});}
 }
 const result=[];
 for(const blink of [0,.5,1])for(const corrected of (blink===1?[false,true]:[true])){
  const weights={eyeBlinkLeft:blink,eyeBlinkRight:blink,...(corrected&&blink===1?Object.fromEntries(SEAL_NAMES.map(n=>[n,1])):{})},skin=frontSurface(posed(body,weights)),row={blink,corrected,sampled_eye_surface:samples.length,exposed_samples:0,eyes:{}};
  for(const side of ['Left','Right']){const points=samples.filter(p=>p.side===side);let exposed=0;for(const p of points)if(p.z>skin(p.x,p.y)+.00005)exposed++;row.eyes[side]={samples:points.length,exposed};row.exposed_samples+=exposed;}
  row.exposed_fraction=row.exposed_samples/samples.length;result.push(row);
 }
 return {schema:'jali-eye-coverage-audit-v1',grid_step_mm:step*1000,depth_tolerance_mm:.05,poses:result,independent_human_approval:false,independent_implementation:false,limits:'Model-space forward orthographic sampled coverage, not all-view continuous collision proof, corneal thickness, anatomical approval or physical AV. Original source geometry/morphs are retained.'};
}
