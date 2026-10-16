const path = require('node:path');
require('esbuild').build({
  entryPoints: ['web/neural-head/viewer.js'], bundle: true, minify: true,
  format: 'iife', target: 'es2020', nodePaths: [path.resolve('tools/node_modules')],
  outfile: process.argv[2] || 'artifacts/neural-head-demo/viewer.js', legalComments: 'inline'
}).catch(error => { console.error(error); process.exitCode = 1; });
