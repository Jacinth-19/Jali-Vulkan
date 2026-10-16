import test from 'node:test';
import assert from 'node:assert/strict';
import {summarizeFrames} from '../web/playback-checkpoint/measurement.mjs';
test('empty and one-frame observations do not invent FPS',()=>{
 assert.equal(summarizeFrames([]).observed_render_fps,null);
 assert.equal(summarizeFrames([{wallTime:10,audioTime:0,renderMs:2}]).observed_render_fps,null);
});
test('reports actual intervals and nearest-rank p95, not requested FPS',()=>{
 const result=summarizeFrames([0,40,80,160].map((t,i)=>({wallTime:t,audioTime:t/1000,renderMs:i+1})));
 assert.equal(result.observed_render_fps,18.75);assert.equal(result.p95_frame_gap_ms,80);
 assert.equal(result.median_frame_gap_ms,40);assert.equal(result.p95_cpu_submission_ms,4);
});
test('nonfinite and nonmonotonic observations are rejected',()=>{
 for(const frames of [null,[{wallTime:NaN,audioTime:0,renderMs:1}],[{wallTime:0,audioTime:-1,renderMs:0}],
 [{wallTime:1,audioTime:0,renderMs:0},{wallTime:1,audioTime:0,renderMs:0}],[{wallTime:1,audioTime:0,renderMs:-1}]])assert.throws(()=>summarizeFrames(frames));
});
