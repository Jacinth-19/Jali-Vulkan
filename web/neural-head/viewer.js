import {eyeClearancePose,EYE_SEAL_NAMES} from './eye-clearance.mjs';
import {rendererLease} from './renderer-lease.mjs';
import {studioPath} from './studio-path.mjs';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { FXAAShader } from 'three/examples/jsm/shaders/FXAAShader.js';
import {creativeSettings} from './creative.mjs';
import {appearanceSettings,BACKGROUNDS} from './appearance.mjs';
import {enhanceSurfaceMaterials,surfaceLighting} from './surface-materials.mjs';
import { composePerformance } from './performance.mjs';
import { sampleClipVisemes, validateCues } from './visemes.mjs';

const $ = id => document.getElementById(id);
const data = window.JALI_HEAD_DATA;
const audio = $('audio');
const canvas = $('face');
const leaseAbort=new AbortController();
let environmentTarget=null;
let initializing=true,releaseLease=null,leaseState='starting';
let sourceAssociations,importedHeadBasis=null,importedParentBasis=null;
let root, controls, camera, renderer, headBone, baseHeadRotation;
const eyeBones=[], gazeRotation=new THREE.Quaternion(), gazeEuler=new THREE.Euler();
let selected = 0, speechMeshes = [], ready = false, frameCount = 0, fpsEpoch = performance.now();
let nativeActive=false, renderSettings={fps:30,resolution:Infinity,pixelRatio:Math.min(devicePixelRatio||1,1.5)}, articulationProfile='baseline';
let creativeOptions=null, appearance=null, composer=null,fxaaPass=null, lights=null,portraitTarget=null,currentLayers=null;
let surfaceShading=null;
let idleRate=2,actualAsset={lod:'full',sha256:data.rig?.model_sha256};
const idleEpoch=performance.now();
let diagnosticPose=null,diagnosticClearance=true,eyeClearanceSupported=false;
let currentPose = {}, modelStats = {}, captureOnly = false, resizeViewer;
const scene = new THREE.Scene();
scene.background = new THREE.Color('#101a1d');
const error = message => { $('error').textContent = message; $('error').hidden = !message; };
const track = () => data.clips[selected];

function selectClip(index, autoplay = false) {
  if (!Number.isInteger(index) || !data.clips[index]) throw new Error('Unknown clip');
  audio.pause(); selected = index;
  const clip = track();
  audio.src = clip.file; audio.load();
  $('clip-title').textContent = clip.title;
  $('transcript').textContent = clip.text;
  $('cue-count').textContent = `${clip.cues.length} estimated mouth cues`;
  document.querySelectorAll('[data-clip]').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.clip) === index)));
  audio.dataset.session = clip.id || '';
  window.dispatchEvent(new CustomEvent('jali-clip-selected', {detail:clip}));
  const timeline = $('timeline'); timeline.replaceChildren();
  for (const cue of clip.cues) {
    const button = document.createElement('button');
    button.style.flexGrow = String(cue.end - cue.start);
    button.style.background = { A:'#e5a77f',B:'#83ada2',C:'#a5c7b2',D:'#edc782',E:'#b9abd0',F:'#82b7ce',G:'#bba06f',H:'#a3b17e',X:'#344b4b' }[cue.value];
    button.title = `${cue.value}: ${cue.start.toFixed(2)}–${cue.end.toFixed(2)} s`;
    button.setAttribute('aria-label', `Seek to ${cue.start.toFixed(2)} seconds, mouth shape ${cue.value}`);
    button.addEventListener('click', () => { audio.currentTime = cue.start; });
    timeline.append(button);
  }
  renderAt(0);
  if (autoplay && ready) audio.play().catch(failure => error(failure.message));
}

function applyAt(time) {
  const clip = track();
  const offset = Number($('trim').value) / 1000;
  const sample = sampleClipVisemes(clip, time, offset, $('sync').checked,articulationProfile);
  const layers=composePerformance(sample.weights,{time,duration:clip?.duration||0,
    life:$('life').checked,mood:$('mood').value,gaze:$('gaze')?.value||'forward',creative:creativeOptions?{...creativeOptions,offset:(clip?._stream_start_sample||0)/(clip?.audio?.sample_rate||24000),idle:!clip,idleTime:((performance.now()-idleEpoch)/1000)%3600}:null});
  currentLayers=layers;
  const pose=eyeClearancePose(diagnosticPose||layers.pose,eyeClearanceSupported&&(!captureOnly||diagnosticClearance));
  for (const mesh of speechMeshes) {
    mesh.morphTargetInfluences.fill(0);
    for (const [name, value] of Object.entries(pose)) {
      const index = mesh.morphTargetDictionary[name];
      if (index !== undefined) mesh.morphTargetInfluences[index] = Math.min(1, Math.max(0, value));
    }
  }
  if (headBone) {
    headBone.rotation.copy(baseHeadRotation);
    if(importedParentBasis){const motion=new THREE.Quaternion().setFromEuler(new THREE.Euler(0,layers.head.yaw,layers.head.roll));headBone.quaternion.premultiply(importedParentBasis.clone().invert().multiply(motion).multiply(importedParentBasis));}
    else {headBone.rotation.y += layers.head.yaw;headBone.rotation.z += layers.head.roll;}
  }
  gazeRotation.setFromEuler(gazeEuler.set(layers.eyes.pitch,layers.eyes.yaw,0));
  if(importedHeadBasis)gazeRotation.premultiply(importedHeadBasis.clone().invert()).multiply(importedHeadBasis);
  // Premultiply in the shared Head-parent frame, not each differently oriented
  // eye bone's Euler axes (which would make left/right eyes diverge).
  for(const {bone,base} of eyeBones)bone.quaternion.copy(base).premultiply(gazeRotation);
  currentPose = pose;
  $('shape').textContent = sample.value;
  $('shape-label').textContent = sample.label;
  $('clock').textContent = clip ? `${time.toFixed(2)} / ${clip.duration.toFixed(2)} s` : 'Ready for a new performance';
  $('trim-value').textContent = `${$('trim').value} ms`;
  canvas.dataset.audioTime = time.toFixed(6);
  canvas.dataset.streamSample = clip?String((clip._stream_start_sample||0)+Math.round(time*(clip.audio?.sample_rate||24000))):'';
  canvas.dataset.shape = sample.value;
  canvas.dataset.speechWeight = String(Math.max(0, ...Object.values(sample.weights)));
  canvas.dataset.playing = String(!audio.paused && !audio.ended);
  canvas.dataset.clip = String(selected);
  canvas.dataset.pose = JSON.stringify(pose);
}

function renderAt(time, updateOrbit = true) {
  if (!ready) return;
  const started = performance.now();
  applyAt(time);
  if (updateOrbit) controls.update();
  if(!nativeActive){if(appearance?.fxaa&&composer)composer.render();else renderer.render(scene, camera);}
  if (window.JALI_RENDER_DIAGNOSTICS) window.dispatchEvent(new CustomEvent('jali-render', {detail:{
    wallTime:performance.now(), audioTime:time, renderMs:performance.now()-started,
    playing:!audio.paused && !audio.ended, seeking:audio.seeking
  }}));
}

async function init() {
  releaseLease=await rendererLease(navigator.locks,state=>{leaseState=state;if(state==='waiting')$('loading').textContent='Another tab may own the character. Close it or use Unload resources there; this tab waits without downloading/decoding a model.';},leaseAbort.signal);
  leaseAbort.signal.throwIfAborted();
  data.clips.forEach(clip => validateCues(clip.cues, clip.duration));
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
  camera = new THREE.PerspectiveCamera(32, 1, 0.01, 20);
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  environmentTarget=pmrem.fromScene(room,0.04);scene.environment=environmentTarget.texture;
  room.dispose(); pmrem.dispose();
  const fill=new THREE.HemisphereLight(0xfaf4e9, 0x36545c, 1.1);scene.add(fill);
  const key = new THREE.DirectionalLight(0xffebd0, 2); key.position.set(-2, 3, 4); scene.add(key);
  const rim = new THREE.DirectionalLight(0x8dcced, 1.3); rim.position.set(2, 2, -1); scene.add(rim);lights={key,rim,fill};
  let bytes;
  if(new URLSearchParams(location.search).get('lod')==='low'){
   if(!data.lod||data.lod.source_sha256!==data.rig.model_sha256)throw Error('No matching prepared low LOD; switch to Full');
   const response=await fetch(studioPath(data.lod.file),{signal:leaseAbort.signal});if(!response.ok)throw Error('Prepared low LOD is unavailable');bytes=new Uint8Array(await response.arrayBuffer());
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(hash!==data.lod.sha256)throw Error('LOD identity mismatch');actualAsset={lod:'low',sha256:hash};
  }else if(data.live&&window.JALI_HEAD_MODEL_URL){
   const response=await fetch(studioPath(window.JALI_HEAD_MODEL_URL),{signal:leaseAbort.signal});if(!response.ok)throw Error('Prepared model unavailable');bytes=new Uint8Array(await response.arrayBuffer());
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(hash!==data.rig.model_sha256)throw Error('Model identity mismatch');
  }else bytes=Uint8Array.from(atob(window.JALI_HEAD_BASE64), c => c.charCodeAt(0));
  delete window.JALI_HEAD_BASE64;
  leaseAbort.signal.throwIfAborted();
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  const gltf = await loader.parseAsync(bytes.buffer, '');
  sourceAssociations=gltf.parser.associations;
  root = gltf.scene;leaseAbort.signal.throwIfAborted(); scene.add(root); root.updateMatrixWorld(true);
  surfaceShading=enhanceSurfaceMaterials(root,THREE,{enabled:new URLSearchParams(location.search).get('surface')!=='original'});
  actualAsset={...actualAsset,shading:surfaceShading.version};
  const geometries = new Set(), bones = new Set();
  root.traverse(object => {
    if (object.isMesh) {
      geometries.add(object.geometry);
      if (object.morphTargetDictionary) speechMeshes.push(object);
    }
    if (object.isBone) bones.add(object);
    if (object.isBone && object.name.toLowerCase() === 'head') headBone = object;
    if (object.isBone && ['LeftEye','RightEye'].includes(object.name)) eyeBones.push({bone:object,base:object.quaternion.clone()});
  });
  const facial = speechMeshes.find(mesh => mesh.morphTargetDictionary.viseme_aa !== undefined);
  if (!facial || !headBone || eyeBones.length!==2 || eyeBones.some(({bone})=>bone.parent!==headBone)) throw new Error('Expected facial visemes, Head and head-parented eye bones are missing');
  // The downloadable asset retains all 66 facial controls. The viewer uploads
  // only controls used by this demo, avoiding 66-way zero-weight shader loops.
  const originalFaceControls = Object.keys(facial.morphTargetDictionary).length;
  eyeClearanceSupported=EYE_SEAL_NAMES.every(n=>Object.hasOwn(facial.morphTargetDictionary,n))&&(Array.isArray(facial.material)?facial.material:[facial.material]).some(m=>m.userData?.jaliEyeClearance==='jali-eye-clearance-v1');
  const used = new Set([...EYE_SEAL_NAMES,'viseme_PP','viseme_I','viseme_SS','viseme_E','viseme_aa','viseme_O','viseme_RR','viseme_U','viseme_FF','viseme_nn','viseme_DD','eyeBlinkLeft','eyeBlinkRight','mouthSmileLeft','mouthSmileRight','cheekSquintLeft','cheekSquintRight','browInnerUp','browOuterUpLeft','browOuterUpRight','browDownLeft','browDownRight','mouthFrownLeft','mouthFrownRight','eyeWideLeft','eyeWideRight']);
  for (const mesh of speechMeshes) {
    const entries = Object.entries(mesh.morphTargetDictionary).filter(([name]) => used.has(name));
    for (const type of Object.keys(mesh.geometry.morphAttributes)) {
      const original = mesh.geometry.morphAttributes[type];
      if (entries.length) mesh.geometry.morphAttributes[type] = entries.map(([, index]) => original[index]);
      else delete mesh.geometry.morphAttributes[type];
    }
    mesh.morphTargetDictionary = Object.fromEntries(entries.map(([name], index) => [name,index]));
    mesh.morphTargetInfluences = entries.map(() => 0);
  }
  baseHeadRotation = headBone.rotation.clone();
  if(data.rig?.profile==='canonical-face-v1'){root.updateMatrixWorld(true);importedHeadBasis=headBone.getWorldQuaternion(new THREE.Quaternion());importedParentBasis=headBone.parent.getWorldQuaternion(new THREE.Quaternion());}
  const target = headBone.getWorldPosition(new THREE.Vector3()); target.y += 0.04;
  camera.position.copy(target).add(new THREE.Vector3(0.035, 0.005, 0.82));
  controls = new OrbitControls(camera, canvas); controls.target.copy(target);portraitTarget=target.clone();
  controls.enableDamping = true; controls.enablePan = false;
  controls.minDistance = 0.38; controls.maxDistance = 2.8;
  controls.maxPolarAngle = Math.PI * 0.68;
  const vertices = [...geometries].reduce((sum, geometry) => sum + geometry.attributes.position.count, 0);
  modelStats = { vertices, bones: bones.size, faceControls: originalFaceControls, authoredEyeCorrectives:eyeClearanceSupported?2:0,sourceFaceControls:originalFaceControls-(eyeClearanceSupported?2:0),runtimeFaceControls: Object.keys(facial.morphTargetDictionary).length, morphMeshes: speechMeshes.length };
  $('vertices').textContent = vertices.toLocaleString();
  $('bones').textContent = String(bones.size);
  $('controls').textContent = String(modelStats.faceControls);
  $('loading').hidden = true;
  document.querySelectorAll('[data-clip]').forEach(button => button.disabled = false);
  ready = true; canvas.dataset.ready = 'true';
  window.dispatchEvent(new Event('jali-head-ready'));
  const resize = resizeViewer = () => {
    if (!ready||captureOnly) return;
    const width = canvas.clientWidth, height = canvas.clientHeight;
    renderer.setPixelRatio(Math.min(renderSettings.pixelRatio,renderSettings.resolution/Math.max(width,height)));
    renderer.setSize(width, height, false);syncPost(); camera.aspect = width / height; camera.updateProjectionMatrix();
    renderAt(audio.currentTime || 0);
  };
  new ResizeObserver(resize).observe(canvas); resize();
  let last = 0;
  function tick(now) {
    requestAnimationFrame(tick);
    if (!ready||document.hidden||nativeActive || captureOnly || now - last < 1000 / ((!audio.paused&&!audio.ended)?renderSettings.fps:Math.min(idleRate,renderSettings.fps))) return;
    last = now;
    const playing = !audio.paused && !audio.ended;
    const orbitChanged = controls.update();
    if (!playing && !orbitChanged && !(!track()&&creativeOptions?.natural&&$('life').checked)) return; // Idle does not consume a software-rendered core.
    renderAt(audio.currentTime || 0, false); frameCount++;
    if (now - fpsEpoch >= 1000) {
      $('fps').textContent = `${(frameCount * 1000 / (now - fpsEpoch)).toFixed(0)} fps`;
      fpsEpoch = now; frameCount = 0;
    }
  }
  requestAnimationFrame(tick);
}

document.querySelectorAll('[data-clip]').forEach(button => button.addEventListener('click', () => selectClip(Number(button.dataset.clip), true)));
$('trim').addEventListener('input', () => renderAt(audio.currentTime || 0));
$('mood').addEventListener('change', () => renderAt(audio.currentTime || 0));
$('sync').addEventListener('change', () => renderAt(audio.currentTime || 0));
$('life').addEventListener('change', () => renderAt(audio.currentTime || 0));
$('gaze')?.addEventListener('change', () => renderAt(audio.currentTime || 0));
for (const event of ['seeked','loadedmetadata','pause','ended']) audio.addEventListener(event, () => {
  if (!captureOnly) renderAt(audio.currentTime || 0);
  if (audio.paused || audio.ended) $('fps').textContent = track() ? 'paused' : 'idle';
});
audio.addEventListener('play', () => { fpsEpoch = performance.now(); frameCount = 0; });
audio.addEventListener('error', () => error(data.live ? 'The local recording could not be loaded. Generate again or refresh the studio.' : 'The audio file could not be loaded. Extract the complete ZIP before opening index.html.'));
if (data.clips.length) selectClip(0);
function syncPost(){
 if(composer){composer.setPixelRatio(renderer.getPixelRatio());composer.setSize(canvas.width/renderer.getPixelRatio(),canvas.height/renderer.getPixelRatio());fxaaPass.material.uniforms.resolution.value.set(1/canvas.width,1/canvas.height);}
}
function setAppearance(value){
 if(!ready)throw Error('Wait for the head to load');
 const previousCamera=appearance?.camera||'portrait';appearance=appearanceSettings(value);const a=appearance;
 scene.background.set(BACKGROUNDS[a.background]);renderer.toneMappingExposure=a.exposure;
 const l=surfaceLighting(a.lighting,surfaceShading?.version!=='original');
 lights.key.intensity=l[0];lights.rim.intensity=l[1];lights.fill.intensity=l[2];
 root.traverse(o=>{if(!o.isMesh)return;for(const m of (Array.isArray(o.material)?o.material:[o.material])){
  if(m.userData.jaliWrap)m.userData.jaliWrap.value=a.scattering;
  if(m.name==='Human.body'){m.roughness=a.skin;m.envMapIntensity=m.userData.jaliSurface==='skin'?.38:.9;}
  if(m.name==='Human.high-poly'||m.userData.jaliSurface==='eyes'){m.roughness=a.eyes;m.metalness=0;m.envMapIntensity=m.userData.jaliSurface?1.05:1.4;if(m.userData.jaliSurface)m.clearcoatRoughness=Math.max(.025,Math.min(.1,a.eyes*.35));}
 }});
 const position={portrait:[.035,.005,.82],close:[.015,.015,.57],threequarter:[.33,.025,.78],wide:[.02,-.04,1.22]}[a.camera];
 if(previousCamera!==a.camera){controls.target.copy(portraitTarget);camera.position.copy(portraitTarget).add(new THREE.Vector3(...position));controls.update();}
 if(a.fxaa&&!composer){composer=new EffectComposer(renderer);composer.addPass(new RenderPass(scene,camera));fxaaPass=new ShaderPass(FXAAShader);composer.addPass(fxaaPass);composer.addPass(new OutputPass());}
 syncPost();renderAt(audio.currentTime||0);
}
function disposeScene(){
 const geometries=new Set(),materials=new Set(),textures=new Set(),skeletons=new Set();
 root?.traverse(o=>{if(!o.isMesh)return;if(o.skeleton)skeletons.add(o.skeleton);geometries.add(o.geometry);for(const m of(Array.isArray(o.material)?o.material:[o.material])){materials.add(m);for(const value of Object.values(m))if(value?.isTexture)textures.add(value);}});
 if(root)scene.remove(root);for(const g of geometries)g.dispose();for(const t of textures)t.dispose();for(const m of materials)m.dispose();for(const s of skeletons)s.dispose();
 controls?.dispose();for(const pass of composer?.passes||[])pass.dispose?.();composer?.dispose();environmentTarget?.dispose();environmentTarget=null;scene.environment=null;renderer?.renderLists.dispose();renderer?.dispose();renderer?.forceContextLoss();
 speechMeshes=[];eyeBones.length=0;sourceAssociations=null;headBone=null;root=null;currentPose={};diagnosticPose=null;ready=false;canvas.dataset.ready='false';releaseLease?.();releaseLease=null;
}
window.JaliHeadDemo = {
  setIdleRate:value=>{if(![2,15].includes(value))throw Error('Invalid idle rate');idleRate=value;},
  unload:()=>{if(captureOnly)throw Error('Finish export before unloading');leaseAbort.abort();audio.pause();audio.removeAttribute('src');audio.load();window.JALI_HEAD_BASE64=null;for(const c of data.clips)if(c.file.startsWith('blob:'))URL.revokeObjectURL(c.file);data.clips=[];selected=-1;ready=false;canvas.dataset.ready='false';if(!initializing)disposeScene();},

  holdDiagnosticPose:(pose,clearance=true)=>{
    if(typeof clearance!=='boolean')throw Error('Invalid diagnostic clearance flag');
    if(!ready||nativeActive||!captureOnly||!audio.paused)throw Error('Diagnostic pose needs paused capture mode');
    const known=new Set(speechMeshes.flatMap(m=>Object.keys(m.morphTargetDictionary)));
    if(pose!==null&&(!pose||Array.isArray(pose)||Object.keys(pose).length>80||Object.entries(pose).some(([k,v])=>!known.has(k)||!Number.isFinite(v)||v<0||v>1)))throw Error('Invalid diagnostic pose');
    diagnosticClearance=clearance;diagnosticPose=pose?{...pose}:null;renderAt(0);return {diagnostic:true,pose:currentPose};
  },
  pickDiagnosticLandmark:(x,y)=>{
    if(!ready||nativeActive||!captureOnly||![x,y].every(v=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=1))throw Error('Picking needs capture mode and normalized canvas coordinates');
    root.updateMatrixWorld(true);for(const mesh of speechMeshes)mesh.skeleton?.update();const ray=new THREE.Raycaster();ray.setFromCamera(new THREE.Vector2(x*2-1,1-y*2),camera);
    const hit=ray.intersectObject(root,true).find(h=>speechMeshes.includes(h.object));if(!hit?.face)throw Error('No diagnostic face mesh at that point');
    const mesh=hit.object,ids=[hit.face.a,hit.face.b,hit.face.c],v=ids.map(i=>mesh.getVertexPosition(i,new THREE.Vector3()).applyMatrix4(mesh.matrixWorld)),bary=THREE.Triangle.getBarycoord(hit.point,...v,new THREE.Vector3());
    return {model_sha256:actualAsset.sha256,anchor:{mesh:mesh.name,vertices:ids.map((index,i)=>({index,weight:Math.max(0,Math.min(1,bary.toArray()[i]))}))},point_metres:hit.point.toArray(),pose:{...currentPose},human_anatomy_or_contact_verified:false};
  },
  diagnosticLayout:()=>{if(!ready||!captureOnly)throw Error('Diagnostic layout needs capture mode');return {model_sha256:actualAsset.sha256,meshes:speechMeshes.map(m=>({name:m.name,vertices:m.geometry.attributes.position.count,controls:Object.keys(m.morphTargetDictionary)}))};},
  diagnosticVertices:(name,ids)=>{
    if(!ready||nativeActive||!captureOnly||!Array.isArray(ids)||ids.length>64)throw Error('Diagnostic vertex sampling needs capture mode and <=64 indices');
    const meshes=speechMeshes.filter(m=>m.name===name);if(meshes.length!==1)throw Error('Expected unique speech mesh');const mesh=meshes[0];root.updateMatrixWorld(true);mesh.skeleton?.update();
    return ids.map(i=>{if(!Number.isInteger(i)||i<0||i>=mesh.geometry.attributes.position.count)throw Error('Invalid landmark index');return mesh.getVertexPosition(i,new THREE.Vector3()).applyMatrix4(mesh.matrixWorld).toArray();});
  },
  setCreative: value=>{creativeOptions=creativeSettings(value);renderAt(audio.currentTime||0);},
  setAppearance,

  setArticulation: value => {articulationProfile=value;renderAt(audio.currentTime||0);},
  setPerformance: value => {renderSettings={...value};if(ready&&!captureOnly&&resizeViewer)resizeViewer();},
  setNativeMode: enabled => {nativeActive=Boolean(enabled);canvas.style.visibility=nativeActive?'hidden':'visible';renderAt(audio.currentTime||0);},
  updateClock: time => renderAt(time),
  selectClip: index => selectClip(index, false),
  resetPerformance: (clearStyle=false) => {
    if(clearStyle){$('mood').value='neutral';if($('gaze'))$('gaze').value='forward';}
    for(const old of data.clips.filter(c=>c._transient))if(old.file.startsWith('blob:'))URL.revokeObjectURL(old.file);
    data.clips=data.clips.filter(c=>!c._transient);
    audio.pause(); audio.removeAttribute('src'); audio.load(); selected = -1;
    audio.dataset.session = ''; $('timeline').replaceChildren();
    $('clip-title').textContent = 'Preparing a new performance';
    $('transcript').textContent = ''; $('cue-count').textContent = '';
    renderAt(0);
  },
  loadSession: (clip,transient=false) => {
    validateCues(clip.cues, clip.duration);
    if (!ready || !data.live || !/^[a-f0-9]{32}$/.test(clip.id) || typeof clip.text !== 'string'
        || JSON.stringify(clip.rig) !== JSON.stringify(data.rig)) throw new Error('Session does not match the loaded rig');
    audio.pause();
    for(const old of data.clips.filter(c=>c._transient))if(old.file.startsWith('blob:'))URL.revokeObjectURL(old.file);
    data.clips=data.clips.filter(c=>!c._transient);
    data.clips.push({...clip,_transient:transient});
    if (!transient && data.clips.length > 6) {
      const old = data.clips.shift();
      if (old.file.startsWith('blob:')) URL.revokeObjectURL(old.file);
    }
    selectClip(data.clips.length - 1, false);
    renderAt(0);
    return data.clips.length - 1;
  },
  getDiagnostics: () => {
    const gl = renderer?.getContext(), extension = gl?.getExtension('WEBGL_debug_renderer_info');
    return {surfaceShading:nativeActive?null:surfaceShading,renderAsset:nativeActive?{lod:'native-fixed',sha256:data.rig?.model_sha256}:actualAsset,idleRate, activeRenderer:nativeActive?'native-vulkan':'WebGL', modelStats, webgl:gl ? {
      version:gl.getParameter(gl.VERSION),
      renderer:gl.getParameter(extension ? extension.UNMASKED_RENDERER_WEBGL : gl.RENDERER),
      vendor:gl.getParameter(extension ? extension.UNMASKED_VENDOR_WEBGL : gl.VENDOR),
      contextLost:gl.isContextLost()
    } : null, canvas:{width:canvas.width,height:canvas.height}, pixelRatio:renderer?.getPixelRatio(),
    speechRig:data.rig || null };
  },
  getState: () => ({ ready,leaseState,eyeClearance:{supported:eyeClearanceSupported,enabled:!captureOnly||diagnosticClearance,diagnosticOverride:captureOnly&&!diagnosticClearance},surfaceShading:nativeActive?null:surfaceShading,renderAsset:nativeActive?{lod:'native-fixed',sha256:data.rig?.model_sha256}:actualAsset,idleRate, layers:currentLayers, creative:creativeOptions,appearance,streamOffset:(track()?._stream_start_sample||0)/(track()?.audio?.sample_rate||24000),idleTime:creativeOptions?.natural?((performance.now()-idleEpoch)/1000)%3600:0, sessionId: track()?.id || null, clips: data.clips.map(c => ({id:c.id, title:c.title})), modelStats, gazeBones:eyeBones.map(({bone,base})=>{const e=new THREE.Euler().setFromQuaternion(bone.quaternion.clone().multiply(base.clone().invert()));return {name:bone.name,delta:{x:Math.abs(e.x)<1e-12?0:e.x,y:Math.abs(e.y)<1e-12?0:e.y}};}), pose: currentPose, time: audio.currentTime, clip: selected,
    activeMorphs: speechMeshes.map(mesh => ({ mesh: mesh.name, values: Object.fromEntries(Object.entries(mesh.morphTargetDictionary).filter(([, i]) => mesh.morphTargetInfluences[i] > 0.01).map(([name,i]) => [name, mesh.morphTargetInfluences[i]])) })) }),
  referenceVertices: (layout,time,index=selected) => {
    if(index!==selected)selectClip(index,false);renderAt(time);root.updateMatrixWorld(true);
    const meshes=[];root.traverse(o=>{if(o.isSkinnedMesh)meshes.push(o);});const positions=[];
    for(const item of layout){
      const mesh=meshes.find(m=>{const a=sourceAssociations.get(m);return a?.nodes===item.sourceNodeIndex&&(a.primitives??0)===item.primitiveIndex;});
      if(!mesh||mesh.geometry.attributes.position.count!==item.count)throw new Error('Native/source primitive correspondence differs');
      mesh.skeleton.update();const point=new THREE.Vector3();
      for(let i=0;i<item.count;i++){mesh.getVertexPosition(i,point).applyMatrix4(mesh.matrixWorld);positions.push(point.x,point.y,point.z);}
    }
    const bytes=new Uint8Array(new Float32Array(positions).buffer);let binary='';for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));return btoa(binary);
  },
  setCaptureMode: (enabled, size = 512) => {
    if (!ready) throw new Error('Model is not ready');
    if (enabled && (!Number.isInteger(size) || size < 128 || size > 2048)) throw new Error('Invalid capture size');
    captureOnly = Boolean(enabled);if(!captureOnly){diagnosticPose=null;diagnosticClearance=true;}
    if (captureOnly) {
      canvas.style.width = `${size}px`; canvas.style.height = `${size}px`;
      renderer.setPixelRatio(1); renderer.setSize(size, size, false);syncPost();
      camera.aspect = 1; camera.updateProjectionMatrix();
    } else {
      canvas.style.removeProperty('width'); canvas.style.removeProperty('height');
      resizeViewer();
    }
  },
  // Deterministic offline export uses the same sampled cues, not a canned animation.
  capture: (time, index = selected, mime = 'image/png') => {
    if(nativeActive)throw new Error('Use native renderer capture, not WebGL canvas export');
    if (index !== selected) selectClip(index, false);
    renderAt(time); return canvas.toDataURL(mime, 0.92);
  }
};
init().then(()=>{initializing=false;if(leaseAbort.signal.aborted)disposeScene();}).catch(failure => { initializing=false;disposeScene();if(failure.name==='AbortError'){$('loading').textContent='Renderer unloaded. Reload to request ownership again.';return;}error(failure.message); $('loading').textContent = 'Model could not load'; console.error(failure); });
