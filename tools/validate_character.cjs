const fs = require('node:fs');
const validator = require('gltf-validator');
const path = process.argv[2] || 'build-live/assets/android.glb';
validator.validateBytes(new Uint8Array(fs.readFileSync(path))).then(result => {
  console.log(JSON.stringify(result.issues, null, 2));
  if (result.issues.numErrors || result.issues.numWarnings) process.exitCode = 1;
}).catch(error => { console.error(error); process.exitCode = 1; });
