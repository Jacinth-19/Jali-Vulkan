import test from 'node:test';import assert from 'node:assert/strict';
import {validateStreamChunk} from '../web/neural-studio/streaming.mjs';
const chunk={index:0,id:'abc',start_sample:0,end_sample:24000,clip:{id:'abc',duration:1,audio:{sample_rate:24000}}};
test('sample offsets, not arrival times, define chunk order',()=>{assert.equal(validateStreamChunk(chunk,0,0,24000),24000);assert.throws(()=>validateStreamChunk(chunk,1,0,24000));assert.throws(()=>validateStreamChunk(chunk,0,1,24000));});
test('rates, duplicates, gaps, fractional offsets and duration mismatches fail',()=>{for(const changed of [{start_sample:.5},{end_sample:0},{end_sample:24001.5},{id:'wrong'},{clip:{id:'abc',duration:2,audio:{sample_rate:24000}}}])assert.throws(()=>validateStreamChunk({...chunk,...changed},0,0,24000));assert.throws(()=>validateStreamChunk(chunk,0,0,48000));});
