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
