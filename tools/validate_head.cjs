// Validate decoded geometry as well as the compressed GLB container. The official
// validator does not decode EXT_meshopt_compression itself.
const fs = require('node:fs');
const path = require('node:path');
const { NodeIO } = require('@gltf-transform/core');
const { ALL_EXTENSIONS } = require('@gltf-transform/extensions');
const { MeshoptDecoder } = require('meshoptimizer');
const validator = require('gltf-validator');
(async () => {
  await MeshoptDecoder.ready;
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({'meshopt.decoder':MeshoptDecoder});
  const doc = await io.read(process.argv[2] || 'artifacts/neural-head-demo/model/mpfb-head.glb');
  for (const extension of doc.getRoot().listExtensionsUsed()) if (extension.extensionName === 'EXT_meshopt_compression') extension.dispose();
  const decoded = await io.writeBinary(doc);
  const result = await validator.validateBytes(decoded);
  const report = process.argv[3] || 'artifacts/neural-head-demo/proof/decoded-model-validation.json';
  fs.mkdirSync(path.dirname(report), {recursive:true});
  fs.writeFileSync(report, JSON.stringify(result.issues,null,2)+'\n');
  console.log('Decoded model validation:', result.issues.numErrors,'errors,',result.issues.numWarnings,'warnings');
  if (result.issues.numErrors) process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});
