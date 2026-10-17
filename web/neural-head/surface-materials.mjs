// Original bounded hair-card/eye material treatment. No Hair-Renderer-X shader code
// or groom assets are copied. This is NOT strand scattering or a MetaHuman renderer.

export const SURFACE_VERSION='physical-eyes-hair-cards-v1';
const EYES=new Set(['Human.high-poly','Wolf3D_EyeLeft','Wolf3D_EyeRight','Wolf3D_Eye']);
const HAIR=new Set(['Human.ponytail01','Wolf3D_Hair']);
export function surfaceRole(name){return EYES.has(name)?'eyes':HAIR.has(name)?'hair':null;}
export function enhanceSurfaceMaterials(root,THREE,{enabled=true}={}){
 const replacements=new Map(),report={version:enabled?SURFACE_VERSION:'original',eyeMeshes:0,hairMeshes:0,tangentBytes:0,newDrawCalls:0,newTextures:0,limits:'Wet dielectric eye coating and anisotropic hair cards; no refractive corneal geometry, strand groom, voxel scattering or native changes.'};
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
   report[role==='eyes'?'eyeMeshes':'hairMeshes']++;
   if(replacements.has(source))return replacements.get(source);
   const material=new THREE.MeshPhysicalMaterial();
   THREE.MeshStandardMaterial.prototype.copy.call(material,source);
   material.defines={...material.defines,PHYSICAL:''};
   material.userData={...source.userData,jaliSurface:role};material.metalness=0;
   if(role==='eyes'){
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
