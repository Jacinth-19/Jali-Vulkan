// Strict canonical-profile validation. Only the known derivative-TBN tangent warning is allowed.
const fs=require('node:fs'),validator=require('gltf-validator');
(async()=>{
 const result=await validator.validateBytes(new Uint8Array(fs.readFileSync(process.argv[2]))),issues=result.issues;
 fs.writeFileSync(process.argv[3],JSON.stringify(issues,null,2)+'\n');
 const unexpected=issues.messages.filter(m=>m.severity===0||(m.severity===1&&m.code!=='MESH_PRIMITIVE_GENERATED_TANGENT_SPACE'));
 if(issues.numErrors||unexpected.length||issues.numWarnings!==issues.messages.filter(m=>m.severity===1).length)throw Error('Unexpected canonical validator issues: '+JSON.stringify(unexpected));
 console.log(JSON.stringify({errors:issues.numErrors,warnings:issues.numWarnings,allowed_warning:'MESH_PRIMITIVE_GENERATED_TANGENT_SPACE (derivative TBN)',infos:issues.numInfos,hints:issues.numHints}));
})().catch(e=>{console.error(e);process.exitCode=1;});
