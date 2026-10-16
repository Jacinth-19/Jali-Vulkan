// Explicit build-time export. Frozen/native runtime never launches Node.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{pathToFileURL}=require('node:url');
(async()=>{
 const source=path.resolve(__dirname,'../web/neural-head/visemes.mjs');
 const {SHAPES}=await import(pathToFileURL(source).href);
 const output=path.resolve(process.argv[2]||path.join(__dirname,'../web/neural-head/native-shapes.json'));
 fs.mkdirSync(path.dirname(output),{recursive:true});
 fs.writeFileSync(output,JSON.stringify({schema:'jali-native-shapes-v1',retarget_sha256:crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex'),shapes:SHAPES},null,2)+'\n');
})().catch(e=>{console.error(e);process.exitCode=1;});
