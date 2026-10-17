import {Ray,Vector3,Triangle} from 'three';
import {auditEyeClearance} from './audit_eye_clearance.mjs';
import {frontSurface,authorEyeClearance} from './author_eye_clearance.mjs';
// Original build-time appearance recipe, not scanned assets or a strand renderer.
// Input is the checksum-pinned UNCOMPRESSED MakeHuman rest mesh (female or male).
import {pathToFileURL} from 'node:url';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import {spawnSync} from 'node:child_process';
import {meshopt,dedup,prune} from '@gltf-transform/functions';import {MeshoptEncoder} from 'meshoptimizer';
import {io,audit,sha} from './character_assets.mjs';
const VERSION='jali-authored-appearance-v1';
function values(a){return Array.from({length:a.getCount()},(_,i)=>a.getElement(i,[]));}
function attribute(doc,buffer,name,type,array){return doc.createAccessor(name).setType(type).setArray(array).setBuffer(buffer);}
function setGeometry(doc,p,positions,normals,uv,joints,weights,indices,anchors,sourceTargets){
 const buffer=doc.getRoot().listBuffers()[0];
 for(const [key,type,array] of [['POSITION','VEC3',new Float32Array(positions.flat())],['NORMAL','VEC3',new Float32Array(normals.flat())],['TEXCOORD_0','VEC2',new Float32Array(uv.flat())],['JOINTS_0','VEC4',new Uint16Array(joints.flat())],['WEIGHTS_0','VEC4',new Float32Array(weights.flat())]])p.setAttribute(key,attribute(doc,buffer,VERSION+'-'+key,type,array));
 p.setIndices(attribute(doc,buffer,VERSION+'-indices','SCALAR',new Uint16Array(indices)));
 for(const [target,original] of sourceTargets){
  target.setAttribute('POSITION',attribute(doc,buffer,VERSION+'-morph','VEC3',new Float32Array(anchors.flatMap(i=>original.getElement(i,[])))));
  // A ribbon has a new geometric normal, not the source cylinder's normal.
  target.setAttribute('NORMAL',attribute(doc,buffer,VERSION+'-morph-normal','VEC3',new Float32Array(positions.length*3)));
 }
}
export function groomFibers(doc,node,kind,bodyPrimitive,densityImage){
 const skinFront=kind==='brow'&&bodyPrimitive?frontSurface(bodyPrimitive):null;
 const p=node.getMesh().listPrimitives()[0],pos=values(p.getAttribute('POSITION')),js=values(p.getAttribute('JOINTS_0')),ws=values(p.getAttribute('WEIGHTS_0'));
 const targets=p.listTargets().map(t=>[t,t.getAttribute('POSITION')]);
 const positions=[],normals=[],uv=[],joints=[],weights=[],indices=[],anchors=[];
 const count=kind==='brow'?150:48;
 for(const side of [-1,1]){
  const candidates=pos.map((v,i)=>({v,i})).filter(o=>o.v[0]*side>0);
  const xmin=Math.min(...candidates.map(o=>Math.abs(o.v[0]))),xmax=Math.max(...candidates.map(o=>Math.abs(o.v[0])));
  const centerY=candidates.reduce((s,o)=>s+o.v[1],0)/candidates.length;
  const rows=kind==='brow'?[-1,0,1]:[1,-1];
  for(const row of rows)for(let h=0;h<(kind==='lash'&&row===-1?24:count);h++){
   const n=kind==='lash'&&row===-1?24:count,u=(h+.5)/n,x=side*(xmin+(xmax-xmin)*u);
   let local=candidates.filter(o=>Math.abs(o.v[0]-x)<.0018);
   if(kind==='lash')local=local.filter(o=>row>0?o.v[1]>=centerY:o.v[1]<centerY);
   if(!local.length)continue;
   const y=kind==='brow'?local.reduce((s,o)=>s+o.v[1],0)/local.length +row*.00085*Math.sin(Math.PI*u)**.4+Math.sin(h*2.399+row)*.00016 : (row>0?Math.min(...local.map(o=>o.v[1])):Math.max(...local.map(o=>o.v[1])));
   const anchor=local.reduce((a,b)=>Math.abs(a.v[0]-x)+Math.abs(a.v[1]-y)<Math.abs(b.v[0]-x)+Math.abs(b.v[1]-y)?a:b);
   const root=[...anchor.v];if(kind==='brow'){root[0]=x;root[1]=y;}root[2]=Math.max(...local.map(o=>o.v[2]))+(kind==='brow'?.0006:.00015);
   const length=kind==='brow'?(.0018+.0007*(.5+.5*Math.sin(h*1.7+row)))*(.45+.55*Math.sin(Math.PI*u)**.3):row>0?.0021+.0011*Math.sin(Math.PI*u):.0012;
   const dx=side*(kind==='brow'?length*(.2+1.1*u):.00045*(2*u-1)),dy=(kind==='brow'?(1-1.25*u):row)*length,dz=kind==='brow'?.00025:.0017;
   const width=kind==='brow'?.00018*(.4+.6*Math.sin(Math.PI*u)**.3):.00014,base=positions.length;
   for(let k=0;k<3;k++){const t=k/2,w=width*(1-.94*t);for(const edge of [-1,1]){
    const vertex=[root[0]+dx*t+edge*w/2,root[1]+dy*t,root[2]+dz*t*t];if(skinFront){const z=skinFront(vertex[0],vertex[1]);if(Number.isFinite(z))vertex[2]=Math.max(vertex[2],z+.0003);}
    const nearest=local.reduce((a,b)=>Math.hypot(...a.v.map((q,k)=>q-vertex[k]))<Math.hypot(...b.v.map((q,k)=>q-vertex[k]))?a:b);
    positions.push(vertex);normals.push([0,0,1]);uv.push([edge<0?0:1,t]);joints.push(js[nearest.i]);weights.push(ws[nearest.i]);anchors.push(nearest.i);
   }}
   indices.push(base,base+1,base+2,base+1,base+3,base+2,base+2,base+3,base+4,base+3,base+5,base+4);
  }
 }
 if(!positions.length||positions.length>6000)throw Error('Invalid bounded fiber recipe');
 setGeometry(doc,p,positions,normals,uv,joints,weights,indices,anchors,targets);
 let densityVertices=0;
 if(kind==='brow'&&densityImage){
  const q=doc.createPrimitive(),dp=[],dn=[],du=[],dj=[],dw=[],di=[],da=[],N=64;
  for(const side of [-1,1]){const candidates=pos.map((v,i)=>({v,i})).filter(o=>o.v[0]*side>0),xmin=Math.min(...candidates.map(o=>Math.abs(o.v[0]))),xmax=Math.max(...candidates.map(o=>Math.abs(o.v[0]))),start=dp.length;
   for(let j=0;j<=N;j++){const u=j/N,x=side*(xmin+(xmax-xmin)*u),local=candidates.filter(o=>Math.abs(o.v[0]-x)<.002);if(!local.length)throw Error('Missing brow-density anchor');const center=local.reduce((s,o)=>s+o.v[1],0)/local.length+.0004,half=.0002+.0014*Math.sin(Math.PI*u)**.5;
    for(let row=0;row<3;row++){const y=center+(row-1)*half,anchor=local.reduce((a,b)=>Math.hypot(a.v[0]-x,a.v[1]-y)<Math.hypot(b.v[0]-x,b.v[1]-y)?a:b),z=skinFront(x,y);if(!Number.isFinite(z))throw Error('Brow-density skin projection missed');dp.push([x,y,z+.00018]);dn.push([0,0,1]);du.push([u,row/2]);dj.push(js[anchor.i]);dw.push(ws[anchor.i]);da.push(anchor.i);}
   }
   for(let j=0;j<N;j++)for(let row=0;row<2;row++){const a=start+j*3+row,b=a+3,c=a+1,e=b+1;di.push(...(side>0?[a,b,c,b,e,c]:[a,c,b,b,c,e]));}
  }
  const dt=targets.map(([t,a])=>{const n=doc.createPrimitiveTarget(t.getName());q.addTarget(n);return[n,a];});setGeometry(doc,q,dp,dn,du,dj,dw,di,da,dt);
  q.setMaterial(doc.createMaterial('Jali.brow-density').setBaseColorTexture(doc.createTexture('jali-brow-density').setImage(densityImage).setMimeType('image/png')).setBaseColorFactor([.022,.011,.006,1]).setAlphaMode('BLEND').setDoubleSided(false).setMetallicFactor(0).setRoughnessFactor(.98));node.getMesh().addPrimitive(q);densityVertices=dp.length;
 }

 p.getMaterial().setBaseColorTexture(null).setBaseColorFactor([.085,.045,.025,1]).setDoubleSided(true).setAlphaMode('OPAQUE');
 return {kind,old_vertices:pos.length,new_vertices:positions.length,ribbons:positions.length/6,source_morphs:targets.length,density_underlay_vertices:densityVertices,density_underlay_peak_alpha:kind==='brow'?92/255:0,additional_asset_draws:kind==='brow'?1:0,method:'Tapered curved opaque ribbons; per-vertex source-nearest anchors retain original skin weights and all source morph positions; layered brow flow is projected above the rest skin surface. Not a strand simulation or full-blink approval.'};
}
function shortHair(doc,node,eyeY,body,bodyPrimitive,hairImage){
 const p=node.getMesh().listPrimitives()[0],skin=node.getSkin(),head=skin.listJoints().findIndex(j=>j.getName()==='Head');if(head<0)throw Error('Hair must share the known Head skin');
 const top=body.filter(v=>v[1]>eyeY+.045),ymax=Math.max(...top.map(v=>v[1])),xs=top.map(v=>Math.abs(v[0])),zs=top.map(v=>v[2]);
 const cx=0,cy=eyeY+.024,cz=(Math.min(...zs)+Math.max(...zs))/2,rx=Math.max(...xs)*1.035,ry=ymax-cy+.0025,rz=(Math.max(...zs)-Math.min(...zs))*.55+.006;
 const bodyNormals=values(bodyPrimitive.getAttribute('NORMAL')),points=body.map(p=>new Vector3(...p)),faces=[];
 const ids=bodyPrimitive.getIndices().getArray();for(let k=0;k<ids.length;k+=3){const f=Array.from(ids.slice(k,k+3));if(f.every(i=>body[i][1]>eyeY-.065))faces.push(f);}
 const origin=new Vector3(cx,cy,cz),ray=new Ray(),hit=new Vector3(),bary=new Vector3();let misses=0;
 const positions=[],normals=[],uv=[],joints=[],weights=[],indices=[],N=96,M=24;
 for(let j=0;j<=M;j++)for(let i=0;i<=N;i++){
  const theta=2*Math.PI*i/N,limit=1.46-.42*Math.cos(theta)+.045*Math.cos(theta)**12,phi=Math.max(.002,j/M*limit);
  const ridge=.00045*Math.sin(theta*72+phi*3)*Math.sin(phi);
  const guess=new Vector3(rx*Math.sin(phi)*Math.sin(theta),ry*Math.cos(phi),rz*Math.sin(phi)*Math.cos(theta));ray.set(origin,guess.clone().normalize());
  let best=Infinity,point=null,normal=null;
  for(const f of faces)if(ray.intersectTriangle(points[f[0]],points[f[1]],points[f[2]],false,hit)){
   const distance=hit.distanceToSquared(origin);if(distance<best){best=distance;point=hit.clone();Triangle.getBarycoord(hit,points[f[0]],points[f[1]],points[f[2]],bary);normal=new Vector3(...bodyNormals[f[0]]).multiplyScalar(bary.x).addScaledVector(new Vector3(...bodyNormals[f[1]]),bary.y).addScaledVector(new Vector3(...bodyNormals[f[2]]),bary.z).normalize();}
  }
  if(!point){misses++;point=guess.add(origin);normal=ray.direction.clone();}
  positions.push(point.addScaledVector(normal,.0018+ridge).toArray());normals.push(normal.toArray());uv.push([i/N,j/M]);joints.push([head,0,0,0]);weights.push([1,0,0,0]);
 }
 for(let j=0;j<M;j++)for(let i=0;i<N;i++){const a=j*(N+1)+i,b=a+1,c=a+N+1,d=c+1;indices.push(a,c,b,b,c,d);}
 setGeometry(doc,p,positions,normals,uv,joints,weights,indices,[],[]);
 p.getMaterial().setName('Jali.short-crop').setBaseColorTexture(doc.createTexture('jali-short-crop-fiber-color').setImage(hairImage).setMimeType('image/png')).setBaseColorFactor([.55,.5,.45,1]).setAlphaMode('OPAQUE').setDoubleSided(true);
 node.getMesh().setName('jali_short_crop');node.setName('Jali.short-crop');
 return {style:'original short-crop scalp-projected shell with directional ridges and original streak color map',ray_projection_misses:misses,vertices:positions.length,triangles:indices.length/3,head_joint:head,bounds:{cx,cy,cz,rx,ry,rz},not_strand_groom:true};
}
export async function authorAppearance(doc,sex,{python=process.env.JALI_BUILD_PYTHON||'python'}={}){
 if(!['female','male'].includes(sex))throw Error('Explicit character variant required');
 const root=doc.getRoot(),node=root.listNodes().find(n=>n.getName()==='Human'),body=node.getMesh().listPrimitives()[0],a=body.getAttribute('POSITION');
 if(a.getComponentType()!==5126)throw Error('Appearance authoring needs uncompressed world-space rest data, not guessed quantized axes');
 const originalTargets=body.listTargets();const preserved=()=>JSON.stringify([body.getAttribute('POSITION'),body.getAttribute('NORMAL'),...originalTargets.flatMap(t=>t.listAttributes())].map(a=>{const x=a.getArray();return sha(Buffer.from(x.buffer,x.byteOffset,x.byteLength));}));const sourceSignature=preserved();
 const eye=root.listNodes().find(n=>n.getName()==='LeftEye'),eyeY=eye.getWorldTranslation()[1],positions=values(a),material=body.getMaterial(),folder=fs.mkdtempSync(path.join(os.tmpdir(),'jali-skin-'));
 let recipe,hairImage,densityImage;
 try{
  fs.writeFileSync(path.join(folder,'geometry.json'),JSON.stringify({positions,uv:values(body.getAttribute('TEXCOORD_0')),indices:Array.from(body.getIndices().getArray()),eye_y:eyeY}));
  fs.writeFileSync(path.join(folder,'albedo.png'),material.getBaseColorTexture().getImage());
  const result=spawnSync(python,['tools/author_skin_maps.py',path.join(folder,'geometry.json'),path.join(folder,'albedo.png'),folder],{encoding:'utf8',timeout:90000});if(result.status!==0)throw Error(result.stderr||'Skin map bake failed');
  material.getBaseColorTexture().setImage(new Uint8Array(fs.readFileSync(path.join(folder,'albedo.png')))).setMimeType('image/png');
  for(const [name,set] of [['normal','setNormalTexture'],['roughness','setMetallicRoughnessTexture']]){
   const texture=doc.createTexture('jali-authored-'+name).setImage(new Uint8Array(fs.readFileSync(path.join(folder,name+'.png')))).setMimeType('image/png');material[set](texture);
  }
  hairImage=new Uint8Array(fs.readFileSync(path.join(folder,'hair.png')));densityImage=new Uint8Array(fs.readFileSync(path.join(folder,'brow-density.png')));
  material.setNormalScale(.55).setExtras({...material.getExtras(),jaliAuthoredSkin:VERSION});recipe=JSON.parse(fs.readFileSync(path.join(folder,'recipe.json')));
 }finally{fs.rmSync(folder,{recursive:true,force:true});}
 const fibers=[];for(const [name,kind] of [['Human.mindfront_eyebrows_02','brow'],['Human.mindfront_eyelashes_02','lash']])fibers.push(groomFibers(doc,root.listNodes().find(n=>n.getName()===name),kind,body,densityImage));
 const hair=sex==='male'?shortHair(doc,root.listNodes().find(n=>n.getName()==='Human.ponytail01'),eyeY,positions,body,hairImage):null;
 const eyeClearance=authorEyeClearance(doc),eyeCoverage=auditEyeClearance(doc);
 if(preserved()!==sourceSignature)throw Error('Appearance authoring modified the source face geometry/morphs');
 return {source_face_attribute_sha256:JSON.parse(sourceSignature),schema:VERSION,variant:sex,skin:recipe,fibers,hair,fiber_recipe:'surface-projected-flow-v2',eye_clearance:eyeClearance,eye_coverage:eyeCoverage,eye_clearance_code_sha256:sha(fs.readFileSync('tools/author_eye_clearance.mjs')),eye_coverage_code_sha256:sha(fs.readFileSync('tools/audit_eye_clearance.mjs')),authoring_code_sha256:sha(fs.readFileSync('tools/author_character_appearance.mjs')),skin_recipe_code_sha256:sha(fs.readFileSync('tools/author_skin_maps.py')),source_face_positions_unchanged:true,face_speech_targets_unchanged:true,native_compatible:false,artist_or_human_quality_approved:false,scanned_skin:false};
}
if(import.meta.url===pathToFileURL(path.resolve(process.argv[1]||'')).href){
 try{const [input,output,sex,python]=process.argv.slice(2),loader=await io(),doc=await loader.read(input);
 for(const [i,t] of doc.getRoot().listTextures().entries())t.setImage(new Uint8Array(fs.readFileSync(`.cache/lipsync/textures/${i}.png`))).setMimeType('image/png');
 const report=await authorAppearance(doc,sex,{python});
 await MeshoptEncoder.ready;await doc.transform(dedup(),prune(),meshopt({encoder:MeshoptEncoder,level:'medium'}));audit(doc);await loader.write(output,doc);fs.writeFileSync(output+'.json',JSON.stringify({...report,model_sha256:sha(fs.readFileSync(output))},null,2));
 }catch(e){console.error(e);process.exitCode=1;}
}
