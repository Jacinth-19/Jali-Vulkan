// Independent Three.js source skin+morph CPU evaluation vs canonical native CPU/GPU.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
(async()=>{
 const browser=await require('./test_browser.cjs').launch();
 try{
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(process.argv[2]);await page.waitForFunction(()=>window.JaliHeadDemo?.getState().ready,null,{timeout:60000});
  await page.evaluate(()=>{JaliHeadDemo.setCaptureMode(true);document.querySelector('#life').checked=false;document.querySelector('#mood').value='neutral';});
  const source=JSON.parse(fs.readFileSync('artifacts/native-compare/source-articulation.json')),meta=JSON.parse(fs.readFileSync('artifacts/native-head/intermediate/metadata.json')),native=JSON.parse(fs.readFileSync('artifacts/native-head-proof/gpu-reference.json'));
  const layout=meta.primitives.map(p=>({sourceNodeIndex:p.sourceNodeIndex,primitiveIndex:p.primitiveIndex,count:p.count})),probes=[];
  for(const [i,value] of ['X','A','D','G','F','H'].entries()){
   const frame=source.frames.find(f=>f.value===value);if(!frame)throw Error('Missing corpus class '+value);const index=source.corpus.cases.findIndex(c=>c.id===frame.case),clip=source.sessions[index];
   const probe=native.cpu_gpu_poses[i].weights;if(Object.keys(frame.weights).sort().join()!==Object.keys(probe).sort().join()||Object.keys(probe).some(k=>Math.abs(probe[k]-frame.weights[k])>1e-6))throw Error('Reference/corpus pose mismatch '+value);
   const encoded=await page.evaluate(({layout,time,index})=>JaliHeadDemo.referenceVertices(layout,time,index),{layout,time:frame.time,index});
   const b=Buffer.from(encoded,'base64'),actual=new Float32Array(b.buffer,b.byteOffset,b.length/4),refBytes=fs.readFileSync(path.join('artifacts/native-head-proof',native.cpu_gpu_poses[i].position_file)),expected=new Float32Array(refBytes.buffer,refBytes.byteOffset,refBytes.length/4);
   if(actual.length!==expected.length||actual.length!==layout.reduce((n,p)=>n+p.count*3,0))throw Error('Vertex ordering/count differs');
   let max=0,sum=0;for(let k=0;k<actual.length;k++){const error=Math.abs(actual[k]-expected[k]);if(!Number.isFinite(error))throw Error('Nonfinite deformation');max=Math.max(max,error);sum+=error*error;}
   if(max>5e-5)throw Error(`Source Three/native ${value} maximum component error ${max} exceeds 5e-5`);
   probes.push({estimated_class:value,session_id:clip.id,audio_sha256:clip.audio.sha256,time:frame.time,vertices:actual.length/3,maximum_component_error:max,rms_component_error:Math.sqrt(sum/actual.length)});
  }
  if(errors.length)throw Error(JSON.stringify(errors));
  fs.writeFileSync('artifacts/native-head-proof/source-comparison.json',JSON.stringify({passed:true,method:'Three SkinnedMesh.getVertexPosition on ORIGINAL compressed source, all 8 primitive groups in preserved source order, vs native canonical CPU reference already GPU-position/normal tested',probes,layout,source_model_sha256:meta.source_sha256,comparison_viewer_sha256:crypto.createHash('sha256').update(fs.readFileSync('artifacts/native-compare/viewer.js')).digest('hex'),limits:'Positions at actual corpus cue-center times, neutral/no secondary styling. Not identical lighting/pixels, independent phoneme correctness or perceptual acceptance.'},null,2)+'\n');console.log(JSON.stringify(probes));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
