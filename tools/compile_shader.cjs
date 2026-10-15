// Offline SPIR-V compilation using the pinned @webgpu/glslang WASM build.
const fs = require('node:fs');
const glslang = require('@webgpu/glslang')();
const [source, output] = process.argv.slice(2);
if (!source || !output) throw new Error('Usage: node compile_shader.cjs SOURCE OUTPUT');
const stage = source.endsWith('.vert') ? 'vertex' : source.endsWith('.frag') ? 'fragment' : 'compute';
const words = glslang.compileGLSL(fs.readFileSync(source, 'utf8'), stage);
fs.writeFileSync(output, Buffer.from(words.buffer, words.byteOffset, words.byteLength));
