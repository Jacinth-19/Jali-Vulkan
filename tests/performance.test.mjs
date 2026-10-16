import test from 'node:test';
import assert from 'node:assert/strict';
import {composePerformance} from '../web/neural-head/performance.mjs';
import {SHAPES} from '../web/neural-head/visemes.mjs';

test('speech closures, F/V and rounded poses suppress smile without changing speech',()=>{
  for(const key of ['A','E','F','G']){
    const speech={...SHAPES[key].weights};const p=composePerformance(speech,{mood:'warm'}).pose;
    assert.equal(p.mouthSmileLeft,0);assert.equal(p.cheekSquintRight,0);
    for(const [name,value] of Object.entries(speech))assert.equal(p[name],value);
    assert.deepEqual(speech,SHAPES[key].weights);
  }
  assert.equal(composePerformance({}, {mood:'warm'}).pose.mouthSmileLeft,.16);
});
test('layers reset deterministically at audio end and never accumulate',()=>{
  const options={time:2.55,duration:4,life:true,mood:'attentive',gaze:'left'};
  const first=composePerformance({},options);assert.ok(first.pose.eyeBlinkLeft>.99);assert.equal(first.eyes.yaw,.08);
  assert.deepEqual(first,composePerformance({},options));
  const ended=composePerformance({}, {...options,time:4,mood:'neutral',gaze:'forward'});
  assert.deepEqual(ended,{pose:{},head:{yaw:0,roll:0},eyes:{yaw:0,pitch:0}});
});
test('manual gaze bounded and rejects invalid control/clock/weight values',()=>{
  for(const gaze of ['forward','left','right','down']){
    const {eyes}=composePerformance({}, {gaze});assert.ok(Math.abs(eyes.yaw)<=.08&&Math.abs(eyes.pitch)<=.06);
  }
  for(const options of [{time:NaN},{duration:-1},{mood:'inferred'},{gaze:'unknown'}])assert.throws(()=>composePerformance({},options));
  assert.throws(()=>composePerformance({viseme_PP:Infinity}));
});
