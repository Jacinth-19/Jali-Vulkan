import test from 'node:test';import assert from 'node:assert/strict';
import {PRESETS,performanceSettings,summarizeObservation} from '../web/neural-studio/settings.mjs';
import {ARTICULATION,articulation} from '../web/neural-head/articulation.mjs';
import {sampleClipVisemes} from '../web/neural-head/visemes.mjs';
import {AudioPrefetch} from '../web/neural-studio/streaming.mjs';
test('bounded performance settings and measured recommendation, not invented device data',()=>{
 for(const key of Object.keys(PRESETS))assert.deepEqual(performanceSettings(key),PRESETS[key]);
 for(const p of [{fps:NaN},{fps:999,resolution:512,pixelRatio:1},'unknown'])assert.throws(()=>performanceSettings(p));
 assert.throws(()=>summarizeObservation([],PRESETS.balanced));
 const slow=Array.from({length:40},(_,i)=>({time:i*80,cost:50}));assert.equal(summarizeObservation(slow,PRESETS.balanced).recommended_preset,'low');
 const fast=Array.from({length:40},(_,i)=>({time:i*33,cost:4}));assert.equal(summarizeObservation(fast,PRESETS.balanced).recommended_preset,null);
});
test('clear articulation strengthens contacts/tongue, preserves short closures, bounded rest',()=>{
 for(const value of ['A','G','H','F']){
 const clip={duration:.2,cues:[{start:0,end:.1,value},{start:.1,end:.2,value:'D'}]};
 const a=sampleClipVisemes(clip,.02,0,true,'baseline'),b=sampleClipVisemes(clip,.02,0,true,'clear');
 for(const k in a.weights)assert.ok(b.weights[k]>=a.weights[k]);
 assert.deepEqual(sampleClipVisemes(clip,.2,0,true,'clear').weights,{});
 for(let t=0;t<.2;t+=.001)for(const v of Object.values(sampleClipVisemes(clip,t,0,true,'clear').weights))assert.ok(Number.isFinite(v)&&v>=0&&v<=1);
 }
 for(const bad of [{closure:NaN},{tongue:9},{smooth:1},{evil:1},'missing'])assert.throws(()=>articulation(bad));
 assert.equal(articulation('clear').closure,1.05);
});
test('prefetch is two-slot, ordered, reusable and counts decoded hits',async()=>{
 const disposed=[],pool=new AudioPrefetch(async i=>({id:i.id}),v=>disposed.push(v.id));
 pool.add({index:0,id:'a'});pool.add({index:1,id:'b'});assert.throws(()=>pool.add({index:2,id:'c'}));
 await new Promise(r=>setTimeout(r,0));assert.equal((await pool.take({index:0,id:'a'})).id,'a');assert.equal(pool.hits,1);
 pool.close();assert.deepEqual(disposed,['b']);
});
test('late prefetch completion after Stop is disposed and cannot be consumed',async()=>{
 let resolve;const disposed=[],pool=new AudioPrefetch(()=>new Promise(r=>resolve=r),v=>disposed.push(v));pool.add({index:0,id:'a'});
 await Promise.resolve();pool.close();resolve('late');await new Promise(r=>setTimeout(r,0));assert.deepEqual(disposed,['late']);assert.throws(()=>pool.add({index:1,id:'b'}));
});
test('prefetch failure and changed identity never become a playable recording',async()=>{
 const pool=new AudioPrefetch(async()=>{throw Error('bad hash');},()=>{});pool.add({index:0,id:'a'});
 await assert.rejects(pool.take({index:0,id:'changed'}),/identity/);await assert.rejects(pool.take({index:0,id:'a'}),/bad hash/);pool.close();
});
