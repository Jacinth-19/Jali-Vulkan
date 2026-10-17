// Contact landmark intake and mathematics only. Neither a passing distance nor
// supplier-declared review proves anatomical/perceptual contact or independence.
const finite=v=>typeof v==='number'&&Number.isFinite(v);
export function validateContactReference(r,layout,{allowFixture=false}={}){
 if(r?.schema!=='jali-contact-reference-v1'||r.model_sha256!==layout.model_sha256||!/^[a-f0-9]{64}$/.test(r.model_sha256))throw Error('Contact reference must bind the exact rendered GLB, including LOD');
 const provenance=r.provenance;if(!provenance||!['human-reviewed-landmarks',...(allowFixture?['synthetic-fixture']:[])].includes(provenance.kind))throw Error('Reviewed landmark provenance required; fixtures need explicit opt-in');
 for(const k of ['reviewer','method','source'])if(typeof provenance[k]!=='string'||!provenance[k].trim()||provenance[k].length>500)throw Error('Missing bounded landmark provenance');
 if(!Array.isArray(r.cases)||!r.cases.length||r.cases.length>24)throw Error('Use 1-24 contact cases');
 const controls=new Set(layout.meshes.flatMap(m=>m.controls)),ids=new Set();let total=0;
 for(const c of r.cases){
  if(typeof c.id!=='string'||!c.id.trim()||c.id.length>80||ids.has(c.id))throw Error('Unique bounded contact case IDs required');ids.add(c.id);
  if(!c.pose||typeof c.pose!=='object'||Array.isArray(c.pose)||Object.keys(c.pose).length>40||Object.entries(c.pose).some(([k,v])=>!controls.has(k)||k.startsWith('jaliEyeSeal')||!finite(v)||v<0||v>1))throw Error('Invalid held contact pose');
  if(!Array.isArray(c.pairs)||!c.pairs.length||c.pairs.length>16)throw Error('Use 1-16 landmark pairs per case');
  const pairIds=new Set();for(const pair of c.pairs){
   if(++total>128)throw Error('Contact reference exceeds 128 pairs');
   if(typeof pair.id!=='string'||!pair.id.trim()||pair.id.length>80||pairIds.has(pair.id))throw Error('Unique landmark pair ID required');pairIds.add(pair.id);
   if(!['distance','signed-separation'].includes(pair.metric)||!finite(pair.min_mm)||!finite(pair.max_mm)||pair.min_mm>pair.max_mm||pair.min_mm< (pair.metric==='distance'?0:-25)||pair.max_mm>25)throw Error('Explicit bounded distance limits required');
   if(pair.metric==='signed-separation'&&(!Array.isArray(pair.normal)||pair.normal.length!==3||!pair.normal.every(finite)||Math.abs(Math.hypot(...pair.normal)-1)>1e-5))throw Error('Signed separation needs a unit model-world normal');
   for(const point of [pair.a,pair.b]){
    const meshes=layout.meshes.filter(m=>m.name===point?.mesh);if(meshes.length!==1||!Array.isArray(point.vertices)||![1,3].includes(point.vertices.length))throw Error('Unique mesh and vertex/triangle landmark required');
    if(point.vertices.some(v=>!Number.isInteger(v.index)||v.index<0||v.index>=meshes[0].vertices||!finite(v.weight)||v.weight<0||v.weight>1)||Math.abs(point.vertices.reduce((s,v)=>s+v.weight,0)-1)>1e-6)throw Error('Invalid landmark indices/barycentric weights');
   }
   if(JSON.stringify(pair.a)===JSON.stringify(pair.b))throw Error('Landmark pair must not compare a point to itself');
  }
 }
 return r;
}
export function interpolateLandmark(vertices,weights){
 if(!Array.isArray(weights)||![1,3].includes(weights.length)||weights.some(w=>!finite(w)||w<0||w>1)||Math.abs(weights.reduce((a,b)=>a+b,0)-1)>1e-6||!Array.isArray(vertices)||vertices.length!==weights.length||vertices.some(p=>p.length!==3||!p.every(finite)))throw Error('Invalid rendered landmark samples');
 return [0,1,2].map(k=>vertices.reduce((s,p,i)=>s+p[k]*weights[i],0));
}
export function contactMeasurement(pair,a,b){
 const delta=b.map((v,i)=>v-a[i]);if(delta.length!==3||!delta.every(finite))throw Error('Nonfinite contact measurement');
 const value_mm=1000*(pair.metric==='signed-separation'?delta.reduce((s,v,i)=>s+v*pair.normal[i],0):Math.hypot(...delta));
 return {id:pair.id,metric:pair.metric,value_mm,min_mm:pair.min_mm,max_mm:pair.max_mm,within_declared_range:value_mm>=pair.min_mm&&value_mm<=pair.max_mm,physical_or_perceptual_contact_verified:false};
}
