import {sampleClipVisemes,validateCues} from '../neural-head/visemes.mjs';
import {composePerformance} from '../neural-head/performance.mjs';
import {articulation} from '../neural-head/articulation.mjs';
import {creativeSettings} from '../neural-head/creative.mjs';
export function animationTimeline(clip,{fps=30,calibration='clear',creative={},mood='neutral',gaze='forward',life=true,sync=true,trim=0}={}){
 if(![15,24,30,60].includes(fps)||!Number.isFinite(trim)||Math.abs(trim)>.15||!clip?.audio?.sha256||clip.analysis?.audio_sha256!==clip.audio.sha256)throw Error('Invalid export clock or audio binding');
 validateCues(clip.cues,clip.duration);calibration=articulation(calibration);creative=creativeSettings({...creative,offset:0,idle:false,idleTime:0});
 const frames=[];for(let i=0;i<=Math.ceil(clip.duration*fps);i++){
  const time=Math.min(i/fps,clip.duration),speech=sampleClipVisemes(clip,time,trim,sync,calibration).weights;
  const layers=composePerformance(speech,{time,duration:clip.duration,life,mood,gaze,creative});frames.push({time,...layers});
 }
 return {schema:'jali-facial-animation-v1',session_id:clip.id,audio_sha256:clip.audio.sha256,text_sha256:clip.text_sha256,rig:clip.rig,duration:clip.duration,fps,settings:{calibration,creative,mood,gaze,life,sync,trim},frames,limits:'Named morph weights 0–1; head/eye angles in radians in the Jali rig frame. Manual expressions, not inferred emotion. Retargeting/coordinate conversion may be needed in other tools; not FBX or a universal DCC rig.'};
}
export function timelineCSV(timeline){
 const names=[...new Set(timeline.frames.flatMap(f=>Object.keys(f.pose)))].sort();
 return [['time',...names,'head_yaw','head_roll','eye_yaw','eye_pitch'].join(','),...timeline.frames.map(f=>[f.time,...names.map(k=>f.pose[k]||0),f.head.yaw,f.head.roll,f.eyes.yaw,f.eyes.pitch].join(','))].join('\n');
}
