// Development-only pinned browser harness, not a runtime dependency of the app.
const fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib'),{execFileSync}=require('node:child_process'),{chromium:playwright}=require('playwright-core');
exports.launch=async()=>{
 if(process.platform==='win32'||process.env.JALI_BROWSER_CHANNEL)return playwright.launch({channel:process.env.JALI_BROWSER_CHANNEL||'chrome',headless:true,args:['--enable-unsafe-swiftshader']});
 const support=path.resolve('.cache/runtime/browser'),chromium=require('@sparticuz/chromium');fs.mkdirSync(support,{recursive:true});
 fs.writeFileSync(path.join(support,'support.tar'),zlib.brotliDecompressSync(fs.readFileSync(path.join(__dirname,'node_modules/@sparticuz/chromium/bin/al2023.tar.br'))));execFileSync('tar',['-xf',path.join(support,'support.tar'),'-C',support]);
 return playwright.launch({executablePath:await chromium.executablePath(),args:chromium.args,headless:true,env:{...process.env,LD_LIBRARY_PATH:`${support}/lib:/tmp:${process.env.LD_LIBRARY_PATH||''}`}});
};
