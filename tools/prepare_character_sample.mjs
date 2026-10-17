// Build-time only, exact pinned personal-use sample. Never a general URL loader.
import fs from 'node:fs';
import {io,importCharacter,CHANNELS,sha} from './character_assets.mjs';
import {dedup,prune} from '@gltf-transform/functions';
import path from 'node:path';
const [input,output]=process.argv.slice(2);
const expected='8864c504b5c11daa2f0037afffdc0815bb0fa2e6062e37a584746116a3c2f538';
if(!input||!output||fs.statSync(input).size>5*1024*1024||sha(fs.readFileSync(input))!==expected)throw Error('Expected the exact pinned brunette sample');
const loader=await io(),doc=await loader.read(input);
// The source has 17 textures, including duplicates/unreferenced textures. Preserve
// used maps, then apply the NORMAL strict importer (16-texture budget unchanged).
await doc.transform(dedup(),prune());fs.mkdirSync(output,{recursive:true});
const prepared=path.join(output,'sample-normalized.glb');await loader.write(prepared,doc);
const names=new Set(doc.getRoot().listMeshes().flatMap(m=>m.listPrimitives().flatMap(p=>p.listTargets().map(t=>t.getName()))));
const optional=['mouthSmileLeft','mouthSmileRight','cheekSquintLeft','cheekSquintRight','browInnerUp','browOuterUpLeft','browOuterUpRight','browDownLeft','browDownRight','mouthFrownLeft','mouthFrownRight','eyeWideLeft','eyeWideRight'];
const profile={schema:'jali-retarget-v1',name:'Ready Player Me brunette — noncommercial sample',space:'jali-y-up-world-axes-v1',bones:{Head:'Head',LeftEye:'LeftEye',RightEye:'RightEye'},morphs:Object.fromEntries([...CHANNELS,...optional.filter(n=>names.has(n))].map(n=>[n,n])),license:'CC BY-NC 4.0. Attribution: Ready Player Me / met4citizen TalkingHead. Source https://github.com/met4citizen/TalkingHead/tree/2afe6d79779313db8909badebf46f9805a6c7b70/avatars/brunette.glb . https://creativecommons.org/licenses/by-nc/4.0/ . NOT an Epic MetaHuman; no commercial/public redistribution approval.'};
fs.writeFileSync(path.join(output,'retarget-profile.json'),JSON.stringify(profile,null,2));
const report=await importCharacter(prepared,profile,output);
fs.writeFileSync(path.join(output,'sample-source.json'),JSON.stringify({schema:'jali-personal-sample-v1',source_sha256:expected,normalized_sha256:report.source_sha256,normalization:'deduplicate and prune unused resources only',source_commit:'2afe6d79779313db8909badebf46f9805a6c7b70',license:profile.license,epic_metahuman:false,public_redistribution_approved:false},null,2));
console.log(JSON.stringify({passed:true,output,model_sha256:report.model_sha256,report:report.report}));
