import {test} from 'node:test';
import assert from 'node:assert/strict';
import {studioPath} from '../web/neural-head/studio-path.mjs';
test('scoped studio requests retain canonical session paths and current origin',()=>{
 for(const id of ['female','male']){
  assert.equal(studioPath('/api/config',`/characters/${id}/`),`/characters/${id}/api/config`);
  assert.equal(studioPath('/sessions/abc/audio.wav',`/characters/${id}/`),`/characters/${id}/sessions/abc/audio.wav`);
  assert.equal(studioPath('/model/low.glb',`/characters/${id}/`),`/characters/${id}/model/low.glb`);
 }
});
test('standalone/offline studios and blob URLs remain unchanged',()=>{
 for(const path of ['/api/config','/model/low.glb','blob:local-audio','https://example.invalid/x','//example.invalid/x','style.css'])assert.equal(studioPath(path,'/'),path);
 assert.equal(studioPath('/api/config','/characters/unregistered/'),'/api/config');
});
