import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {surfaceRole,enhanceSurfaceMaterials,SURFACE_VERSION,skinDetail} from '../web/neural-head/surface-materials.mjs';
const THREE=createRequire(import.meta.url)('../tools/node_modules/three');
test('surface roles are explicit, not broad name guesses',()=>{
 assert.equal(surfaceRole('Human.high-poly'),'eyes');assert.equal(surfaceRole('Wolf3D_Eye'),'eyes');
 assert.equal(surfaceRole('Human.ponytail01'),'hair');assert.equal(surfaceRole('Human.body'),'skin');for(const n of ['hairy_skin','unknown','Human.teeth_base'])assert.equal(surfaceRole(n),null);
});
test('wet eyes and anisotropic cards preserve mesh, source texture, alpha and bounded skin detail',()=>{
 const root=new THREE.Group(),texture=new THREE.Texture();
 const eye=new THREE.MeshStandardMaterial({name:'Human.high-poly',map:texture});
 const hair=new THREE.MeshStandardMaterial({name:'Human.ponytail01',map:texture,alphaTest:.3,side:THREE.DoubleSide});
 const skin=new THREE.MeshStandardMaterial({name:'Human.body'});
 for(const m of [eye,hair,skin])root.add(new THREE.Mesh(new THREE.PlaneGeometry(),m));
 const positions=root.children.map(m=>Array.from(m.geometry.attributes.position.array));
 const r=enhanceSurfaceMaterials(root,THREE);
 assert.equal(r.version,SURFACE_VERSION);assert.equal(r.eyeMeshes,1);assert.equal(r.hairMeshes,1);assert.equal(r.newDrawCalls,0);assert.equal(r.newTextures,1);assert.equal(r.skinMeshes,1);assert.equal(r.detailBytes,65536);assert.ok(r.tangentBytes>0&&r.tangentBytes<1024);
 const [e,h,s]=root.children.map(m=>m.material);assert.ok(e.isMeshPhysicalMaterial);assert.ok(Object.hasOwn(e.defines,'PHYSICAL'));assert.equal(e.clearcoat,1);assert.equal(e.ior,1.376);assert.equal(e.map,texture);assert.equal(h.map,texture);assert.equal(h.alphaTest,.3);assert.equal(h.side,THREE.DoubleSide);assert.equal(h.depthWrite,hair.depthWrite);assert.equal(h.transparent,hair.transparent);assert.equal(h.anisotropy,.65);assert.equal(h.forceSinglePass,true);assert.equal(h.alphaToCoverage,true);assert.notEqual(s,skin);assert.equal(s.userData.jaliSurface,'skin');assert.equal(s.envMapIntensity,.38);assert.equal(s.clearcoat,0);assert.ok(s.normalMap.isDataTexture);
 assert.deepEqual(root.children.map(m=>Array.from(m.geometry.attributes.position.array)),positions);
});
test('original comparison leaves materials untouched; unsuitable cards fail back safely',()=>{
 const root=new THREE.Group(),material=new THREE.MeshStandardMaterial({name:'Human.ponytail01'}),g=new THREE.BufferGeometry();root.add(new THREE.Mesh(g,material));
 assert.equal(enhanceSurfaceMaterials(root,THREE,{enabled:false}).version,'original');assert.equal(root.children[0].material,material);
 const r=enhanceSurfaceMaterials(root,THREE);assert.equal(r.hairMeshes,0);assert.equal(root.children[0].material,material);assert.equal(r.tangentBytes,0);
});

test('skin detail is deterministic, bounded, mipmapped and shared without mutating authored maps',()=>{
 const a=skinDetail(THREE),b=skinDetail(THREE);assert.deepEqual(a.image.data,b.image.data);assert.equal(a.image.data.length,65536);assert.equal(a.generateMipmaps,true);assert.equal(a.minFilter,THREE.LinearMipmapLinearFilter);
 const root=new THREE.Group(),source=new THREE.MeshStandardMaterial({name:'Human.body'});
 for(let i=0;i<2;i++)root.add(new THREE.Mesh(new THREE.PlaneGeometry(),source));
 const report=enhanceSurfaceMaterials(root,THREE);assert.equal(report.skinMeshes,2);assert.equal(report.newTextures,1);assert.equal(root.children[0].material,root.children[1].material);
 const shader={fragmentShader:'#include <roughnessmap_fragment>'};root.children[0].material.onBeforeCompile(shader);assert.match(shader.fragmentShader,/vNormalMapUv/);assert.match(shader.fragmentShader,/clamp/);
 const authored=new THREE.Texture(),mat=new THREE.MeshStandardMaterial({name:'Human.body',normalMap:authored}),r=new THREE.Group();r.add(new THREE.Mesh(new THREE.PlaneGeometry(),mat));assert.equal(enhanceSurfaceMaterials(r,THREE).newTextures,0);assert.equal(r.children[0].material.normalMap,authored);
});
