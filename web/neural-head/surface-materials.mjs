// Original bounded hair-card/eye material treatment. No Hair-Renderer-X shader code
// or groom assets are copied. This is NOT strand scattering or a MetaHuman renderer.

export const SURFACE_VERSION='physical-skin-eyes-hair-v2';
const EYES=new Set(['Human.high-poly','Wolf3D_EyeLeft','Wolf3D_EyeRight','Wolf3D_Eye']);
const HAIR=new Set(['Human.ponytail01','Wolf3D_Hair']);
export function surfaceRole(name){return name==='Human.body'?'skin':EYES.has(name)?'eyes':HAIR.has(name)?'hair':null;}

// Original deterministic procedural detail, not scanned skin. One 64 KiB RGBA
// texture per scene, mipmapped to avoid distant pore aliasing; no network/assets.
export function skinDetail(THREE){
 const size=128,height=new Float32Array(size*size),data=new Uint8Array(size*size*4);
 for(let i=0;i<height.length;i++){let n=Math.imul(i+19,1597334677);n=Math.imul(n^(n>>>16),2246822519);height[i]=((n^(n>>>13))>>>0)/4294967295;}
 const at=(x,y)=>height[((y+size)%size)*size+(x+size)%size];
 for(let y=0;y<size;y++)for(let x=0;x<size;x++){
  const i=(y*size+x)*4,dx=(at(x+1,y)-at(x-1,y))*.28,dy=(at(x,y+1)-at(x,y-1))*.28,inv=1/Math.hypot(dx,dy,1);
  data[i]=Math.round(127.5*(1-dx*inv));data[i+1]=Math.round(127.5*(1-dy*inv));data[i+2]=Math.round(127.5*(1+inv));data[i+3]=Math.round(255*at(x,y));
 }
 const texture=new THREE.DataTexture(data,size,size,THREE.RGBAFormat);texture.name='jali-procedural-skin-detail-v1';
 texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.repeat.set(24,24);texture.generateMipmaps=true;
 texture.minFilter=THREE.LinearMipmapLinearFilter;texture.magFilter=THREE.LinearFilter;texture.needsUpdate=true;return texture;
}
export function enhanceSurfaceMaterials(root,THREE,{enabled=true}={}){
 let detail=null;const replacements=new Map(),report={version:enabled?SURFACE_VERSION:'original',eyeMeshes:0,hairMeshes:0,skinMeshes:0,detailBytes:0,tangentBytes:0,newDrawCalls:0,newTextures:0,limits:'Procedural micro-normal/roughness skin and restrained dielectric highlights; no scanned pores or subsurface transport. Wet coated eyes and anisotropic cards; no corneal geometry, strands, voxel scattering or native changes.'};
 if(!enabled)return report;
 root.traverse(mesh=>{
  if(!mesh.isMesh)return;
  const materials=Array.isArray(mesh.material)?mesh.material:[mesh.material];
  const next=materials.map(source=>{
   const role=surfaceRole(source.name);
   if(!role||!source.isMeshStandardMaterial)return source;
   if(role==='hair'){
    // No UV/tangent guessing on unknown or unsuitable meshes. The known cards
    // need an indexed UV basis; keep an unmodified fallback otherwise.
    const g=mesh.geometry;
    if(!g.index||!g.attributes.uv||!g.attributes.normal||!g.attributes.position)return source;
    if(!g.attributes.tangent){g.computeTangents();report.tangentBytes+=g.attributes.tangent.array.byteLength;}
   }
   report[{eyes:'eyeMeshes',hair:'hairMeshes',skin:'skinMeshes'}[role]]++;
   if(replacements.has(source))return replacements.get(source);
   const material=new THREE.MeshPhysicalMaterial();
   THREE.MeshStandardMaterial.prototype.copy.call(material,source);
   material.defines={...material.defines,PHYSICAL:''};
   material.userData={...source.userData,jaliSurface:role};material.metalness=0;
   if(role==='skin'){
    material.ior=1.4;material.roughness=.68;material.specularIntensity=.32;material.clearcoat=0;material.envMapIntensity=.38;
    // Retain authored normal maps when present. Only our generated alpha channel
    // carries procedural roughness variation; do not reinterpret user textures.
    if(!source.normalMap&&mesh.geometry.attributes.uv){
     if(!detail){detail=skinDetail(THREE);report.newTextures++;report.detailBytes=detail.image.data.byteLength;}
     material.normalMap=detail;material.normalScale.set(.22,.22);
     material.onBeforeCompile=shader=>{shader.fragmentShader=shader.fragmentShader.replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\nroughnessFactor = clamp(roughnessFactor * mix(0.82, 1.12, texture2D(normalMap, vNormalMapUv).a), 0.32, 1.0);');};
     material.customProgramCacheKey=()=>'jali-procedural-skin-v1';
    }
   }else if(role==='eyes'){
    // A clear wet dielectric layer preserves the original iris/sclera texture.
    // No fabricated painted highlights: catchlights come from actual lighting.
    material.ior=1.376;material.clearcoat=1;material.clearcoatRoughness=.04;
    material.roughness=.12;material.envMapIntensity=1.05;
   }else{
    material.roughness=.62;material.anisotropy=.65;material.anisotropyRotation=Math.PI/2;
    material.specularIntensity=.4;material.specularColor.set('#baa48c');
    material.sheen=.12;material.sheenColor.set('#725037');material.sheenRoughness=.55;
    material.envMapIntensity=.55;material.alphaToCoverage=true;
    // Keep the asset's alpha cutoff, textures, skinning and depth-write contract.
    // MSAA coverage works on multisampled targets; FXAA alone is not MSAA.
    material.forceSinglePass=true;
   }
   replacements.set(source,material);return material;
  });
  mesh.material=Array.isArray(mesh.material)?next:next[0];
 });
 // Loader-owned originals have been replaced everywhere in this scene; texture
 // ownership stays with replacements. dispose() does not dispose shared textures.
 for(const material of replacements.keys())material.dispose();
 return report;
}
