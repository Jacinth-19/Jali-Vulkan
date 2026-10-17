// Real generated-asset checks, invoked after the explicit pinned build in CI.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import path from 'node:path';
import {io,CHANNELS,sha} from './character_assets.mjs';
const out=process.argv[2]||'artifacts/male-character',loader=await io();
const male=await loader.read(path.join(out,'character.glb')),female=await loader.read('.cache/lipsync/mpfb.glb');
const source=JSON.parse(fs.readFileSync(path.join(out,'male-source.json'))),manifest=JSON.parse(fs.readFileSync(path.join(out,'character.json')));
assert.equal(manifest.validator_errors,0);assert.equal(manifest.model_sha256,sha(fs.readFileSync(path.join(out,'character.glb'))));assert.equal(source.uv_matched_vertices,11779);assert.equal(source.targets.length,8);
const meshes=male.getRoot().listMeshes();
for(const mesh of meshes){
 const original=female.getRoot().listMeshes().find(m=>m.getName()===mesh.getName());assert.ok(original);
 const p=mesh.listPrimitives()[0],f=original.listPrimitives()[0];
 assert.equal(p.getAttribute('POSITION').getCount(),f.getAttribute('POSITION').getCount());
 assert.deepEqual(p.listTargets().map(t=>t.getName()).sort(),f.listTargets().map(t=>t.getName()).sort());
}
const body=meshes.find(m=>m.getName()==='base').listPrimitives()[0],names=body.listTargets().map(t=>t.getName());for(const name of CHANNELS)assert.ok(names.includes(name));
assert.ok(source.changes.find(m=>m.mesh==='base').max_displacement_m>.01,'Must change genuine geometry, not just profile/voice');
assert.ok(source.changes.find(m=>m.mesh==='high-poly').max_displacement_m>.01,'Rigid eyes must move with the changed stature');
for(const name of ['Head','LeftEye','RightEye']){
 const a=male.getRoot().listNodes().find(n=>n.getName()===name).getWorldMatrix(),b=female.getRoot().listNodes().find(n=>n.getName()===name).getWorldMatrix(),offset=source.bone_rest_offsets_m[name];
 for(let axis=0;axis<3;axis++)assert.ok(Math.abs(a[12+axis]-b[12+axis]-offset[axis])<1e-5,'Refitted pivot must follow shape change');
 for(let i=0;i<12;i++)assert.ok(Math.abs(a[i]-b[i])<1e-6,'Preserve rest orientations');
}
console.log(JSON.stringify({passed:true,model_sha256:manifest.model_sha256,report:manifest.report,source},null,2));
