// Explicit offline canonicalization. Never drop meshes, joints or named targets.
const fs=require('node:fs'),path=require('node:path');
const {NodeIO}=require('@gltf-transform/core');
const {ALL_EXTENSIONS}=require('@gltf-transform/extensions');
const {MeshoptDecoder}=require('meshoptimizer');
const {Matrix4,Matrix3,Vector3}=require('three');
(async()=>{
  await MeshoptDecoder.ready;
  const io=new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
  const input=process.argv[2]||'artifacts/neural-head-demo/model/mpfb-head.glb';
  const output=process.argv[3]||'artifacts/native-head/intermediate';fs.mkdirSync(output,{recursive:true});
  if(fs.statSync(input).size>192*1024*1024)throw Error('Source GLB exceeds 192 MiB');
  const bytes=fs.readFileSync(input);if(bytes.length<28||bytes.toString('ascii',0,4)!=='glTF'||bytes.readUInt32LE(4)!==2||bytes.readUInt32LE(8)!==bytes.length||bytes.readUInt32LE(16)!==0x4e4f534a)throw Error('Expected bounded GLB v2');
  const original=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
  if((original.buffers||[]).some(b=>b.uri)||(original.images||[]).some(i=>i.uri))throw Error('External/data URI resources disabled; use embedded GLB');
  if((original.extensionsUsed||[]).some(e=>!['EXT_meshopt_compression','KHR_mesh_quantization'].includes(e)))throw Error('Unsupported source extension');
  const doc=await io.read(input),root=doc.getRoot(),nodes=root.listNodes();
  if(root.listAnimations().length)throw Error('Authored tracks are not supported by the canonical static bind profile');
  if([...root.listMeshes(),...nodes].some(m=>m.getWeights().some(w=>w!==0)))throw Error('Bake or clear nonzero default morph weights explicitly');
  const slots=[],mapping=new Map(),inverse=[],bindShapes=new Map();
  // Meshopt quantization adds a per-mesh bind shape to inverse binds. Bake
  // exactly that common right-hand transform into positions and deltas, never
  // substitute another mesh's inverse binds or silently truncate skinning.
  for(const skin of root.listSkins()){
    const ibm=skin.getInverseBindMatrices(),joints=skin.listJoints();
    const matrices=joints.map((_,i)=>ibm?ibm.getElement(i,[]):new Matrix4().toArray());
    const shared=joints.findIndex(j=>mapping.has(j));let bind=new Matrix4();
    if(shared>=0)bind.fromArray(inverse[mapping.get(joints[shared])]).invert().multiply(new Matrix4().fromArray(matrices[shared]));
    if(Math.abs(bind.determinant())<1e-20)throw Error('Singular bind shape');
    bindShapes.set(skin,bind);const invBind=bind.clone().invert();
    joints.forEach((joint,i)=>{
      const matrix=new Matrix4().fromArray(matrices[i]).multiply(invBind).toArray();
      if(mapping.has(joint)){
        if(matrix.some((v,k)=>Math.abs(v-inverse[mapping.get(joint)][k])>1e-4))throw Error('Non-common per-joint inverse binds require a richer palette profile');
      }else{mapping.set(joint,slots.length);slots.push(joint);inverse.push(matrix);}
    });
  }
  for(let i=0;i<slots.length;i++){const p=slots[i].getParentNode();if(p&&!mapping.has(p)){mapping.set(p,slots.length);slots.push(p);inverse.push([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);}}
  if(slots.length>128)throw Error('128 joint canonical palette exceeded');
  const targetNames=[];
  for(const mesh of root.listMeshes())for(const n of mesh.getExtras().targetNames||[])if(!targetNames.includes(n))targetNames.push(n);
  if(!targetNames.length||targetNames.length>80)throw Error('Expected 1-80 named morphs');
  const mats=root.listMaterials(),textures=root.listTextures();
  const materials=mats.map((m,i)=>{
    if(m.getMetallicRoughnessTexture()||m.getOcclusionTexture()||m.getEmissiveTexture()||m.listExtensions().length||m.getEmissiveFactor().some(v=>v!==0)||m.getBaseColorTextureInfo()?.listExtensions().length||m.getNormalTextureInfo()?.listExtensions().length)throw Error('Native profile requires base-color-only PBR material: '+m.getName());
    const texture=m.getBaseColorTexture(),normal=m.getNormalTexture();
    if(normal)fs.writeFileSync(path.join(output,`texture-${textures.indexOf(normal)}.bin`),normal.getImage());
    if(m.getBaseColorTextureInfo()?.getTexCoord()>0||m.getNormalTextureInfo()?.getTexCoord()>0)throw Error('Only UV0 supported');
    if(texture){fs.writeFileSync(path.join(output,`texture-${textures.indexOf(texture)}.bin`),texture.getImage());}
    return {name:m.getName(),factor:m.getBaseColorFactor(),metallic:m.getMetallicFactor(),roughness:m.getRoughnessFactor(),alphaMode:m.getAlphaMode(),alphaCutoff:m.getAlphaCutoff(),doubleSided:m.getDoubleSided(),texture:texture?textures.indexOf(texture):-1,normal:normal?textures.indexOf(normal):-1,normalScale:m.getNormalScale(),wrapS:m.getBaseColorTextureInfo()?.getWrapS()??33071,wrapT:m.getBaseColorTextureInfo()?.getWrapT()??33071,normalWrapS:m.getNormalTextureInfo()?.getWrapS()??33071,normalWrapT:m.getNormalTextureInfo()?.getWrapT()??33071};
  });
  const buffers=[];let byteLength=0;
  function values(a){const result=[];for(let i=0;i<a.getCount();i++)result.push(...a.getElement(i,[]));return result;}
  function array(a,type='float'){
    const data=type==='uint'?new Uint32Array(a):new Float32Array(a),b=Buffer.from(data.buffer);
    const r={offset:byteLength,length:b.length};buffers.push(b);byteLength+=b.length;return r;
  }
  const primitives=[];
  for(const node of nodes){const mesh=node.getMesh();if(!mesh)continue;const skin=node.getSkin();if(!skin)throw Error('Unskinned mesh not allowed in this canonical profile');
    const localNames=mesh.getExtras().targetNames||[];if(new Set(localNames).size!==localNames.length)throw Error('Duplicate source target names');
    for(const [primitiveIndex,p] of mesh.listPrimitives().entries()){
      if(p.listSemantics().some(k=>!['POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0','TANGENT'].includes(k))||p.getMode()!==4||p.getAttribute('JOINTS_1')||p.getAttribute('WEIGHTS_1'))throw Error('Triangle/four-influence profile exceeded');
      const pos=p.getAttribute('POSITION'),n=pos.getCount(),j=values(p.getAttribute('JOINTS_0')),w=values(p.getAttribute('WEIGHTS_0'));
      const localJoints=skin.listJoints();for(let i=0;i<j.length;i++)j[i]=mapping.get(localJoints[j[i]]);
      for(let i=0;i<n;i++){const sum=w.slice(i*4,i*4+4).reduce((a,b)=>a+b,0);if(!(sum>.99&&sum<1.01))throw Error('Invalid influence sum');for(let k=0;k<4;k++)w[i*4+k]/=sum;}
      const uv=p.getAttribute('TEXCOORD_0');if(!uv&&(p.getMaterial()?.getBaseColorTexture()||p.getMaterial()?.getNormalTexture()))throw Error('Missing textured UVs');
      const bind=bindShapes.get(skin),linear=new Matrix3().setFromMatrix4(bind),normalMatrix=new Matrix3().getNormalMatrix(bind);
      const positions=values(pos),normals=values(p.getAttribute('NORMAL')),normalLengths=[];
      function transform(a,m,point=false){const v=new Vector3();for(let i=0;i<a.length;i+=3){v.fromArray(a,i);point?v.applyMatrix4(m):v.applyMatrix3(m);v.toArray(a,i);}return a;}
      transform(positions,bind,true);transform(normals,normalMatrix);
      for(let i=0;i<n;i++){const length=Math.hypot(...normals.slice(i*3,i*3+3));if(length<1e-10)throw Error('Zero normal');normalLengths.push(length);for(let k=0;k<3;k++)normals[i*3+k]/=length;}
      if(localNames.length!==p.listTargets().length)throw Error('Source morph names/count differ');
      const targets={};p.listTargets().forEach((t,i)=>{if(t.listSemantics().some(k=>!['POSITION','NORMAL'].includes(k)))throw Error('Unsupported morph semantic');const name=localNames[i];if(!name)throw Error('Unnamed target');
        const dp=t.getAttribute('POSITION')?transform(values(t.getAttribute('POSITION')),linear):null;
        const dn=t.getAttribute('NORMAL')?transform(values(t.getAttribute('NORMAL')),normalMatrix):null;
        if(dn)for(let i=0;i<n;i++)for(let k=0;k<3;k++)dn[i*3+k]/=normalLengths[i];
        targets[name]={position:dp?array(dp):null,normal:dn?array(dn):null};});
      primitives.push({sourceNodeIndex:nodes.indexOf(node),primitiveIndex,name:node.getName(),material:mats.indexOf(p.getMaterial()),count:n,
        positions:array(positions),normals:array(normals),uv:array(uv?values(uv):Array(n*2).fill(0)),
        joints:array(j,'uint'),weights:array(w),indices:array(p.getIndices()?values(p.getIndices()):Array.from({length:n},(_,i)=>i),'uint'),targets});
    }
  }
  const head=nodes.find(n=>n.getName()==='Head');if(!head)throw Error('Missing Head');const world=head.getWorldMatrix();
  const metadata={source:input,source_sha256:require('node:crypto').createHash('sha256').update(fs.readFileSync(input)).digest('hex'),
    targetNames,materials,primitives,joints:slots.map((n,i)=>({name:n.getName(),parent:n.getParentNode()?mapping.get(n.getParentNode()):-1,local:n.getMatrix(),inverse:inverse[i]})),camera:[world[12],world[13]+.04,world[14],4.2]};
  fs.writeFileSync(path.join(output,'geometry.bin'),Buffer.concat(buffers));fs.writeFileSync(path.join(output,'metadata.json'),JSON.stringify(metadata));
  console.log('Decoded native head',primitives.length,'primitives,',slots.length,'palette nodes,',targetNames.length,'named targets');
})().catch(e=>{console.error(e);process.exitCode=1;});
