// Private local landmark/held-pose inspection. Does not upload the reference,
// declare the supplier's review genuine, infer speech timing or measure AV.
const fs=require('node:fs'),path=require('node:path'),{createHash}=require('node:crypto');
(async()=>{
 const args=process.argv.slice(2),value=k=>{const i=args.indexOf(k);return i<0?null:args[i+1];},url=value('--url'),output=value('--output'),reference=value('--reference'),template=args.includes('--make-template'),fixture=args.includes('--allow-fixture');
 if(!url||!output||template===Boolean(reference))throw Error('Use --url URL --output FILE and either --make-template or --reference FILE');
 const resolved=p=>fs.existsSync(p)?fs.realpathSync(p):path.resolve(p);
 if(reference&&(resolved(reference)===resolved(output)||(fs.existsSync(output)&&fs.statSync(reference).dev===fs.statSync(output).dev&&fs.statSync(reference).ino===fs.statSync(output).ino)))throw Error('Output must not overwrite the reference');
 if(path.extname(output).toLowerCase()!=='.json')throw Error('Output must be a JSON file');
 if(fs.existsSync(output)&&!args.includes('--overwrite-output'))throw Error('Output exists; choose a new path or explicitly use --overwrite-output');
 const {validateContactReference,interpolateLandmark,contactMeasurement}=await import('./contact_reference.mjs');
 let r,bytes;if(reference){if(fs.statSync(reference).size>1024*1024)throw Error('Reference exceeds 1 MiB');bytes=fs.readFileSync(reference);r=JSON.parse(bytes);}
 const browser=await require('./test_browser.cjs').launch(),page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(url);await page.waitForFunction(()=>window.JaliHeadDemo?.getState().ready,null,{timeout:90000});
  await page.evaluate(()=>{document.querySelector('#audio').pause();JaliHeadDemo.setCaptureMode(true,512);});const layout=await page.evaluate(()=>JaliHeadDemo.diagnosticLayout());
  let report;
  if(template)report={schema:'jali-contact-reference-v1',model_sha256:layout.model_sha256,provenance:{kind:'human-reviewed-landmarks',reviewer:'',method:'',source:''},cases:[],layout,instructions:'TEMPLATE ONLY. Independently identify upper/lower lip, upper incisor/lower lip and tongue/palate contact landmarks on this exact GLB. Each point uses mesh and vertices:[{index,weight}], one vertex or three barycentric points. Each pair specifies metric distance or signed-separation (unit normal), min_mm/max_mm. Populate cases:[{id,pose,pairs:[{id,a,b,metric,min_mm,max_mm}]}]. Do not copy inferred speech cues as independent truth. In a paused capture-mode studio, pickDiagnosticLandmark(x,y) accepts normalized canvas coordinates (0..1) and returns the actual hit triangle/barycentric anchor; a human must identify anatomy. No landmarks, thresholds or quality approval are supplied by this template.'};
  else{
   validateContactReference(r,layout,{allowFixture:fixture});const cases=[];
   for(const c of r.cases){await page.evaluate(p=>JaliHeadDemo.holdDiagnosticPose(p),c.pose);const pairs=[];
    for(const pair of c.pairs){const points=[];for(const anchor of [pair.a,pair.b]){const vertices=await page.evaluate(p=>JaliHeadDemo.diagnosticVertices(p.mesh,p.vertices.map(v=>v.index)),anchor);points.push(interpolateLandmark(vertices,anchor.vertices.map(v=>v.weight)));}pairs.push({...contactMeasurement(pair,...points),sampled_world_points_metres:points});}
    cases.push({id:c.id,pose:c.pose,pairs});
   }
   report={schema:'jali-contact-comparison-v1',model_sha256:layout.model_sha256,reference_sha256:createHash('sha256').update(bytes).digest('hex'),provenance:r.provenance,fixture:r.provenance.kind==='synthetic-fixture',cases,all_within_declared_ranges:cases.every(c=>c.pairs.every(p=>p.within_declared_range)),independent_review_verified:false,human_quality_accepted:false,independent_phone_timing_verified:false,physical_av_measured:false,limits:'Rendered skinned/morphed vertex or barycentric point distances in metres, compared to supplier-declared ranges. Externally supplied three-vertex weighted anchors are not checked for triangle membership; the capture picker does return a hit triangle. Not a continuous surface collision test or independent quality verdict. Reviewer identity, landmark anatomy and independence require external review.'};
  }
  if(errors.length)throw Error(JSON.stringify(errors));fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(template?'Unfilled contact template created; no independent reference supplied':'Bound contact landmark measurements written; no automatic quality approval');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
