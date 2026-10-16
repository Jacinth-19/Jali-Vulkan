// Prepare an offline, modest-memory demo asset. Source assets remain outside Git.
const { NodeIO } = require('@gltf-transform/core');
const { ALL_EXTENSIONS } = require('@gltf-transform/extensions');
const { dedup, prune, meshopt } = require('@gltf-transform/functions');
const fs = require('node:fs');
const { MeshoptEncoder } = require('meshoptimizer');
(async () => {
  await MeshoptEncoder.ready;
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.encoder':MeshoptEncoder});
  const doc = await io.read('.cache/lipsync/mpfb.glb');
  doc.getRoot().listTextures().forEach((texture, i) => texture.setImage(fs.readFileSync(`.cache/lipsync/textures/${i}.png`)).setMimeType('image/png'));
  // Preserve all bone weights and all facial targets. Quantize, never truncate.
  await doc.transform(dedup(), prune(), meshopt({ encoder: MeshoptEncoder, level:'medium', quantizePosition:16, quantizeNormal:8, quantizeTexcoord:16, quantizeWeight:16 }));
  fs.mkdirSync('artifacts/neural-head-demo/model', {recursive:true});
  await io.write('artifacts/neural-head-demo/model/mpfb-head.glb', doc);
  console.log('Prepared asset bytes:', fs.statSync('artifacts/neural-head-demo/model/mpfb-head.glb').size);
})().catch(e => {console.error(e); process.exitCode=1;});
