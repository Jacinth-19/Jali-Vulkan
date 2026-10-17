// Build-only geometric corrective: the supplied closed eyelid retreats into the
// eyeball. Move intersecting closed-lid vertices forward, never hide/shrink eyes.
// Original rest geometry and original 66 body morphs are not edited.
import {Ray,Vector3} from 'three';
export const SEAL_NAMES=['jaliEyeSealLeft','jaliEyeSealRight'];
export function frontSurface(primitive){
 const a=primitive.getAttribute('POSITION'),points=Array.from({length:a.getCount()},(_,i)=>new Vector3(...a.getElement(i,[]))),indices=primitive.getIndices().getArray(),faces=[];
 for(let i=0;i<indices.length;i+=3){const v=[points[indices[i]],points[indices[i+1]],points[indices[i+2]]];faces.push({v,x0:Math.min(...v.map(p=>p.x)),x1:Math.max(...v.map(p=>p.x)),y0:Math.min(...v.map(p=>p.y)),y1:Math.max(...v.map(p=>p.y))});}
 const ray=new Ray(),hit=new Vector3();
 return (x,y)=>{ray.set(new Vector3(x,y,1),new Vector3(0,0,-1));let z=-Infinity;for(const f of faces)if(x>=f.x0-1e-9&&x<=f.x1+1e-9&&y>=f.y0-1e-9&&y<=f.y1+1e-9&&ray.intersectTriangle(...f.v,false,hit))z=Math.max(z,hit.z);return z;};
}
export function authorEyeClearance(doc,{margin=.0008,maxOffset=.012}={}){
 if(!Number.isFinite(margin)||margin<0||margin>.0015||!Number.isFinite(maxOffset)||maxOffset<.001||maxOffset>.012)throw Error('Bounded eyelid clearance parameters required');
 const r=doc.getRoot(),eye=r.listNodes().find(n=>n.getName()==='Human.high-poly').getMesh().listPrimitives()[0],front=frontSurface(eye),buffer=r.listBuffers()[0],report=[];
 for(const nodeName of ['Human','Human.mindfront_eyelashes_02']){
  const mesh=r.listNodes().find(n=>n.getName()===nodeName).getMesh(),p=mesh.listPrimitives()[0],pos=p.getAttribute('POSITION'),originalWeights=mesh.getWeights(),skinFront=nodeName==='Human'?frontSurface(p):null;
  for(const [side,name] of ['Left','Right'].map((s,i)=>[s,SEAL_NAMES[i]])){
   if(p.listTargets().some(t=>t.getName()===name))throw Error('Eye clearance already authored');
   const blink=p.listTargets().find(t=>t.getName()==='eyeBlink'+side)?.getAttribute('POSITION');if(!blink)throw Error('Required source blink missing');
   const delta=new Float32Array(pos.getCount()*3);let corrected=0,maximum=0;
   for(let i=0;i<pos.getCount();i++){
    const v=pos.getElement(i,[]),d=blink.getElement(i,[]);if(Math.hypot(...d)<.00003)continue;if(skinFront&&v[2]<skinFront(v[0],v[1])-.0006)continue;
    const q=v.map((x,k)=>x+d[k]),z=front(q[0],q[1]);if(!Number.isFinite(z))continue;
    const offset=Math.max(0,z+margin-q[2]);if(offset>maxOffset)throw Error(`Eye clearance offset exceeds ${maxOffset*1000}mm on ${nodeName}/${side}: vertex ${i}, rest ${v}, closed ${q}, offset ${offset*1000}mm`);
    if(offset>0){delta[i*3+2]=offset;corrected++;maximum=Math.max(maximum,offset);}
   }
   const accessor=doc.createAccessor(name).setType('VEC3').setArray(delta).setBuffer(buffer),normals=doc.createAccessor(name+'-normal').setType('VEC3').setArray(new Float32Array(delta.length)).setBuffer(buffer);
   p.addTarget(doc.createPrimitiveTarget(name).setAttribute('POSITION',accessor).setAttribute('NORMAL',normals));report.push({mesh:nodeName,name,corrected_vertices:corrected,maximum_offset_mm:maximum*1000});
  }
  if(nodeName==='Human')p.getMaterial().setExtras({...p.getMaterial().getExtras(),jaliEyeClearance:'jali-eye-clearance-v1'});
  // Preserve explicit default weights, extending only the new channels with zero.
  if(originalWeights.length)mesh.setWeights([...originalWeights,0,0]);
  for(const n of r.listNodes().filter(n=>n.getMesh()===mesh))if(n.getWeights().length)n.setWeights([...n.getWeights(),0,0]);
 }
 return {schema:'jali-eye-clearance-v1',margin_mm:margin*1000,max_offset_mm:maxOffset*1000,activation:'smoothstep at original blink 0.7..1, zero at neutral/half blink',original_morphs_unchanged:true,eyes_hidden_or_scaled:false,world_front_clearance_only:true,human_anatomical_approval:false,meshes:report};
}
