import test from 'node:test';
import assert from 'node:assert/strict';
import { SHAPES, sampleVisemes, sampleClipVisemes, validateCues } from '../web/neural-head/visemes.mjs';
const cues = [{ start:0,end:0.2,value:'X' },{ start:0.2,end:0.6,value:'A' },{ start:0.6,end:1,value:'D' },{ start:1,end:1.4,value:'F' },{ start:1.4,end:1.6,value:'X' }];

test('valid audio timeline and three distinct articulation classes', () => {
  assert.equal(validateCues(cues,1.6),true);
  assert.equal(sampleVisemes(cues,0.3).weights.viseme_PP,0.95);
  assert.equal(sampleVisemes(cues,0.7).weights.viseme_aa,0.88);
  assert.equal(sampleVisemes(cues,1.1).weights.viseme_U,0.88);
});
test('silence, negative timing trim, endpoint, and disabled lipsync rest', () => {
  for(const t of [-0.15,0.1,1.5,1.6,2])assert.deepEqual(sampleVisemes(cues,t).weights,{});
  assert.deepEqual(sampleVisemes(cues,0.7,false).weights,{});
});
test('bounded anticipation blends the actual neighboring controls', () => {
  const p=sampleVisemes(cues,0.99).weights;
  assert.ok(p.viseme_aa>0 && p.viseme_aa<0.88);
  assert.ok(p.viseme_U>0 && p.viseme_U<0.88);
});
test('seeking is deterministic and independent of previous calls', () => {
  const pose=sampleVisemes(cues,0.33); sampleVisemes(cues,1.3);
  assert.deepEqual(sampleVisemes(cues,0.33),pose);
});
test('invalid and nonfinite timelines are rejected', () => {
  for(const bad of [[],[{start:0,end:1.6,value:'toString'}],[{start:0,end:NaN,value:'X'}],[{start:0.2,end:1.6,value:'X'}],[{start:0,end:2,value:'X'}]])assert.throws(()=>validateCues(bad,1.6));
  assert.throws(()=>sampleVisemes(cues,Infinity));
});
test('all mapped weights remain finite and within range', () => {
  for(let t=0;t<1.7;t+=0.001)for(const v of Object.values(sampleVisemes(cues,t).weights))assert.ok(Number.isFinite(v) && v>=0 && v<=1);
  assert.equal(Object.keys(SHAPES).length,9);
});

test('short closures keep a full central hold instead of being blended away', () => {
  for(const duration of [0.01,0.02,0.03,0.1]) {
    const short=[{start:0,end:duration,value:'A'},{start:duration,end:duration+0.2,value:'D'}];
    assert.equal(sampleVisemes(short,duration*0.5).weights.viseme_PP,0.95);
    const transition=sampleVisemes(short,duration*0.9).weights;
    assert.ok(transition.viseme_PP>0 && transition.viseme_aa>0);
  }
});
test('actual audio end rests even with rounded cue ends and negative trim', () => {
  const clip={duration:0.996,cues:[{start:0,end:1,value:'D'}]};
  assert.equal(sampleClipVisemes(clip,0.9).weights.viseme_aa,0.88);
  for(const trim of [-0.15,0,0.15])assert.deepEqual(sampleClipVisemes(clip,clip.duration,trim).weights,{});
  assert.deepEqual(sampleClipVisemes(clip,-0.01,0.15).weights,{});
});
test('clip-aware sampler rejects nonfinite input and handles empty studio', () => {
  assert.deepEqual(sampleClipVisemes(null,0).weights,{});
  assert.throws(()=>sampleClipVisemes({duration:0,cues},0));
  assert.throws(()=>sampleClipVisemes({duration:1.6,cues},0,NaN));
});
