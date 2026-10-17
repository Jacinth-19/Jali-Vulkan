import {authorAppearance} from './author_character_appearance.mjs';
// Build-only finalization; strict common importer and limits are unchanged.
import fs from 'node:fs';
import path from 'node:path';
import {meshopt,dedup,prune} from '@gltf-transform/functions';
import {MeshoptEncoder} from 'meshoptimizer';
import {io,importCharacter,CHANNELS} from './character_assets.mjs';
const [output]=process.argv.slice(2);
const loader=await io(),doc=await loader.read(path.join(output,'male-source.glb'));
// Use the same explicitly prepared, 1024px textures as the stock female build.
for(const [i,texture] of doc.getRoot().listTextures().entries())texture.setImage(fs.readFileSync(`.cache/lipsync/textures/${i}.png`)).setMimeType('image/png');
const enhanced=process.argv.includes('--appearance-v4');
if(enhanced){const report=await authorAppearance(doc,'male',{python:process.argv[process.argv.indexOf('--appearance-v4')+1]});fs.writeFileSync(path.join(output,'appearance-assets.json'),JSON.stringify(report,null,2));}
await MeshoptEncoder.ready;await doc.transform(dedup(),prune(),meshopt({encoder:MeshoptEncoder,level:'medium'}));
await loader.write(path.join(output,'male-source.glb'),doc);
const optional=['mouthSmileLeft','mouthSmileRight','cheekSquintLeft','cheekSquintRight','browInnerUp','browOuterUpLeft','browOuterUpRight','browDownLeft','browDownRight','mouthFrownLeft','mouthFrownRight','eyeWideLeft','eyeWideRight'];
const names=new Set(doc.getRoot().listMeshes().flatMap(m=>m.listPrimitives().flatMap(p=>p.listTargets().map(t=>t.getName()))));
const profile={schema:'jali-retarget-v1',name:'MakeHuman male — official gender-target variant',space:'jali-y-up-world-axes-v1',bones:{Head:'Head',LeftEye:'LeftEye',RightEye:'RightEye'},morphs:Object.fromEntries([...CHANNELS,...optional.filter(n=>names.has(n))].map(n=>[n,n])),license:'CC0 assets: MakeHuman Community MPFB 2.0.15 / TalkingHead source 2afe6d79779313db8909badebf46f9805a6c7b70. Official male gender targets applied to shared rigged base; shared base outfit; optional original appearance recipe (see appearance-assets.json). See male-source.json and MPFB-ASSETS-CC0.md. Not an Epic MetaHuman. Personal-build redistribution review remains open.'};
fs.writeFileSync(path.join(output,'retarget-profile.json'),JSON.stringify(profile,null,2));
console.log(JSON.stringify(await importCharacter(path.join(output,'male-source.glb'),profile,output),null,2));
