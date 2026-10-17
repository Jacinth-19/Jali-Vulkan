import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {surfaceRole,enhanceSurfaceMaterials,SURFACE_VERSION} from '../web/neural-head/surface-materials.mjs';
const THREE=createRequire(import.meta.url)('../tools/node_modules/three');
test('surface roles are explicit, not broad name guesses',()=>{
 assert.equal(surfaceRole('Human.high-poly'),'eyes');assert.equal(surfaceRole('Wolf3D_Eye'),'eyes');
 assert.equal(surfaceRole('Human.ponytail01'),'hair');for(const n of ['Human.body','hairy_skin','unknown','Human.teeth_base'])assert.equal(surfaceRole(n),null);
});
test('wet eyes and anisotropic cards preserve mesh, source texture, alpha and non-target skin',()=>{
 const root=new THREE.Group(),texture=new THREE.Texture();
 const eye=new THREE.MeshStandardMaterial({name:'Human.high-poly',map:texture});
 const hair=new THREE.MeshStandardMaterial({name:'Human.ponytail01',map:texture,alphaTest:.3,side:THREE.DoubleSide});
 const skin=new THREE.MeshStandardMaterial({name:'Human.body'});
 for(const m of [eye,hair,skin])root.add(new THREE.Mesh(new THREE.PlaneGeometry(),m));
 const positions=root.children.map(m=>Array.from(m.geometry.attributes.position.array));
 const r=enhanceSurfaceMaterials(root,THREE);
 assert.equal(r.version,SURFACE_VERSION);assert.equal(r.eyeMeshes,1);assert.equal(r.hairMeshes,1);assert.equal(r.newDrawCalls,0);assert.equal(r.newTextures,0);assert.ok(r.tangentBytes>0&&r.tangentBytes<1024);
 const [e,h,s]=root.children.map(m=>m.material);assert.ok(e.isMeshPhysicalMaterial);assert.ok(Object.hasOwn(e.defines,'PHYSICAL'));assert.equal(e.clearcoat,1);assert.equal(e.ior,1.376);assert.equal(e.map,texture);assert.equal(h.map,texture);assert.equal(h.alphaTest,.3);assert.equal(h.side,THREE.DoubleSide);assert.equal(h.depthWrite,hair.depthWrite);assert.equal(h.transparent,hair.transparent);assert.equal(h.anisotropy,.65);assert.equal(h.forceSinglePass,true);assert.equal(h.alphaToCoverage,true);assert.equal(s,skin);
 assert.deepEqual(root.children.map(m=>Array.from(m.geometry.attributes.position.array)),positions);
});
test('original comparison leaves materials untouched; unsuitable cards fail back safely',()=>{
 const root=new THREE.Group(),material=new THREE.MeshStandardMaterial({name:'Human.ponytail01'}),g=new THREE.BufferGeometry();root.add(new THREE.Mesh(g,material));
 assert.equal(enhanceSurfaceMaterials(root,THREE,{enabled:false}).version,'original');assert.equal(root.children[0].material,material);
 const r=enhanceSurfaceMaterials(root,THREE);assert.equal(r.hairMeshes,0);assert.equal(root.children[0].material,material);assert.equal(r.tangentBytes,0);
});
