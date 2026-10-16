import test from 'node:test';import assert from 'node:assert/strict';
import {creativeSettings,creativePerformance} from '../web/neural-head/creative.mjs';
import {composePerformance} from '../web/neural-head/performance.mjs';
import {profileBook,saveProfile} from '../web/neural-studio/profiles.mjs';
import {appearanceSettings} from '../web/neural-head/appearance.mjs';
import {animationTimeline,timelineCSV} from '../web/neural-studio/export.mjs';
test('rig-scoped named profiles, roundtrip, prototype names and strict import',()=>{
 let book={schema:'jali-character-profiles-v1',rig:'abc',profiles:[]};book=saveProfile(book,'__proto__','clear');assert.equal(book.profiles[0].calibration.closure,1.05);assert.deepEqual(profileBook(JSON.parse(JSON.stringify(book)),'abc'),book);assert.throws(()=>profileBook(book,'other'));assert.throws(()=>saveProfile(book,'bad\nname','clear'));assert.throws(()=>saveProfile(book,'ok',{jaw:NaN}));
 for(let i=0;i<19;i++)book=saveProfile(book,'name'+i,'soft');assert.throws(()=>saveProfile(book,'overflow','clear'));
});
test('new default manual layer preserves all legacy poses',()=>{
 for(const time of [0,.12,2.55,3,4])for(const mood of ['neutral','warm','attentive'])for(const gaze of ['forward','left','right','down']){
  const opts={time,duration:4,life:true,mood,gaze};assert.deepEqual(composePerformance({viseme_PP:.95},opts),composePerformance({viseme_PP:.95},{...opts,creative:{}}));
 }
});
test('timed manual expressions are bounded, fade deterministically and protect speech',()=>{
 const c={intensity:.5,sequence:[{start:0,end:2,fade:.5,expression:'warm',intensity:1},{start:0,end:2,fade:0,expression:'surprise',intensity:1}]};
 const half=creativePerformance({}, {time:.25,duration:3},c),full=creativePerformance({}, {time:1,duration:3},c);
 assert.ok(half.pose.mouthSmileLeft<full.pose.mouthSmileLeft);assert.equal(full.pose.eyeWideLeft,.16);assert.equal(creativePerformance({viseme_PP:.95},{time:1,duration:3},c).pose.mouthSmileLeft,0);assert.deepEqual(creativePerformance({},{time:2,duration:3},c).pose,{});
 for(const bad of [{intensity:NaN},{head:true},{natural:1},{evil:1},{sequence:[{start:0,end:1,expression:'warm',intensity:1,fade:1}]}])assert.throws(()=>creativeSettings(bad));
});
test('natural gaze eases, idle breathes, blinks are irregular and seek reproducible',()=>{
 const c={natural:true,gazeFrom:'forward',gazeStart:1,gazeEase:1,contact:1};
 assert.equal(creativePerformance({},{time:1.5,duration:5,gaze:'left'},c).eyes.yaw,.04);
 const o={time:2,duration:5,life:true};assert.deepEqual(creativePerformance({},o,c),creativePerformance({},o,c));
 assert.notEqual(creativePerformance({},{life:true},{natural:true,idle:true,idleTime:1}).head.yaw,0);
 assert.equal(creativePerformance({},{life:false},{natural:true,idle:true,idleTime:1}).head.yaw,0);
 const centers=[];for(let t=0;t<20;t+=.01)if(creativePerformance({},{time:t,duration:21,life:true},{natural:true}).pose.eyeBlinkLeft>.99)centers.push(t);
 assert.ok(centers.length>=3);
});
test('appearance settings reject unbounded or unknown material/camera changes',()=>{assert.equal(appearanceSettings({fxaa:true}).fxaa,true);for(const value of [{camera:'evil'},{eyes:NaN},{exposure:50},{background:'constructor'}])assert.throws(()=>appearanceSettings(value));});
test('fixed media-clock timeline exports schema, rest, zero-filled CSV and audio binding',()=>{
 const clip={id:'a'.repeat(32),audio:{sha256:'b'.repeat(64)},analysis:{audio_sha256:'b'.repeat(64)},duration:1,cues:[{start:0,end:.5,value:'A'},{start:.5,end:1,value:'X'}],rig:{model_sha256:'rig'},text_sha256:'text'};
 const timeline=animationTimeline(clip,{fps:30,life:false});assert.equal(timeline.frames.length,31);assert.equal(timeline.frames.at(-1).time,1);assert.deepEqual(timeline.frames.at(-1).pose,{});assert.ok(timelineCSV(timeline).includes('viseme_PP'));assert.equal(timelineCSV(timeline).split('\n').length,32);assert.throws(()=>animationTimeline({...clip,analysis:{audio_sha256:'wrong'}}));assert.throws(()=>animationTimeline(clip,{fps:999}));
});

test('all-rest CSV has no phantom empty column',()=>{const csv=timelineCSV({frames:[{time:0,pose:{},head:{yaw:0,roll:0},eyes:{yaw:0,pitch:0}}]});assert.equal(csv.split('\n')[0].split(',').length,csv.split('\n')[1].split(',').length);});

// Exercise bounded cancellation/deadlines with an encoder that never flushes.
// Bundle just as the browser build does, without adding a runtime Node dependency.
import {createRequire} from 'node:module';
import vm from 'node:vm';
import {webcrypto,createHash} from 'node:crypto';
const require=createRequire(import.meta.url);
const recorderBundle=require('../tools/node_modules/esbuild').buildSync({entryPoints:['web/neural-studio/recording.mjs'],bundle:true,write:false,format:'cjs',nodePaths:['tools/node_modules']}).outputFiles[0].text;
function stalledExporter(expire=false){
 let begun;const flushStarted=new Promise(r=>begun=r),locks=[],offers=[],closed=[];
 class Encoder{static async isConfigSupported(){return {supported:true};}state='configured';encodeQueueSize=0;configure(){}encode(){this.encodeQueueSize++;}flush(){begun();return new Promise(()=>{});}close(){this.state='closed';closed.push(this);}}
 class Packet{close(){}}
 const wav=new Uint8Array([1,2,3,4]),sha=createHash('sha256').update(wav).digest('hex');
 const canvas={style:{pointerEvents:'auto'}},head={setCaptureMode(){},updateClock(){},getState:()=>({layers:{pose:{}}})};
 class Decode{async decodeAudioData(){return {duration:.1,numberOfChannels:1,getChannelData:()=>new Float32Array(4800)};}}
 const codecs={VideoEncoder:Encoder,AudioEncoder:Encoder,AudioData:Packet,VideoFrame:Packet,OfflineAudioContext:Decode};
 const document={createElement(){return {getContext(){return {drawImage(){},getImageData(){return {data:new Uint8Array(256*256*4)};}};}};}};
 const module={exports:{}};vm.runInNewContext(recorderBundle,{
  module,...codecs,window:{...codecs,addEventListener(){}},crypto:webcrypto,DOMException,structuredClone,TextEncoder,document,
  setTimeout:expire?(fn)=>{queueMicrotask(fn);return 1;}:setTimeout,clearTimeout:expire?()=>{}:clearTimeout,
  fetch:async()=>({ok:true,arrayBuffer:async()=>wav.buffer})
 });
 const exporter=module.exports.recordingController({audio:{currentTime:0,src:'blob:fixture',pause(){}},canvas,head,getClip:()=>({duration:.1,audio:{sha256:sha},analysis:{audio_sha256:sha}}),getSettings:()=>({fps:30,resolution:256}),lock:v=>locks.push(v),offer:(...args)=>offers.push(args),clear(){},status(){}});
 return {exporter,flushStarted,locks,offers,closed,canvas};
}
test('cancelling a stalled encoder closes both codecs, unlocks controls and offers no movie',async()=>{
 const mock=stalledExporter(),run=mock.exporter.start();await mock.flushStarted;mock.exporter.stop();await assert.rejects(run,/cancelled/);
 assert.equal(mock.exporter.active,false);assert.deepEqual(mock.locks,[true,false]);assert.equal(mock.closed.length,2);assert.equal(mock.offers.length,0);assert.equal(mock.canvas.style.pointerEvents,'auto');
});
test('encoder stall deadline discards output and restores controls',async()=>{
 const mock=stalledExporter(true);await assert.rejects(mock.exporter.start(),/Encoder stalled/);assert.equal(mock.exporter.active,false);assert.deepEqual(mock.locks,[true,false]);assert.equal(mock.closed.length,2);assert.equal(mock.offers.length,0);
});

import {sentenceTurns,castProfiles,conversationDocument} from '../web/neural-studio/dialogue.mjs';
test('dialogue paragraph splitting is bounded and preserves words and speaker identity',()=>{
 let i=0;const turns=sentenceTurns('Hello there. Second sentence!\n'+Array(35).fill('longword').join(' '),'first',()=>String(++i).padStart(32,'0'));
 assert.equal(turns[0].text,'Hello there.');assert.equal(turns[1].text,'Second sentence!');assert.ok(turns.every(t=>t.text.length<=160&&t.speaker==='first'&&t.session===null));assert.equal(turns.slice(2).map(t=>t.text).join(' '),Array(35).fill('longword').join(' '));
 assert.throws(()=>sentenceTurns('x'.repeat(161),'first'));assert.throws(()=>sentenceTurns('One. '.repeat(129),'first'));assert.throws(()=>sentenceTurns('x\0y','first'));
});
test('cast/dialogue schema rejects unknown voices, duplicate identities and stale untrusted fields',()=>{
 const p={id:'first',name:'First',voice:'af_heart',speed:1},t={id:'a'.repeat(32),speaker:'first',text:'Hello.',session:null},doc={schema:'jali-conversation-v1',id:'b'.repeat(32),name:'Test',cast:[p],turns:[t]};
 assert.equal(conversationDocument(doc,['af_heart']).turns.length,1);assert.throws(()=>castProfiles([p,p],['af_heart']));assert.throws(()=>castProfiles([{...p,voice:'uninstalled'}],['af_heart']));assert.throws(()=>castProfiles([{...p,speed:NaN}],['af_heart']));assert.throws(()=>conversationDocument({...doc,turns:[t,t]},['af_heart']));assert.throws(()=>conversationDocument({...doc,turns:[{...t,path:'/secret'}]},['af_heart']));assert.throws(()=>conversationDocument({...doc,turns:[{...t,speaker:'missing'}]},['af_heart']));
});
