export const PRESETS=Object.freeze({low:{fps:15,resolution:256,pixelRatio:.75},balanced:{fps:30,resolution:512,pixelRatio:1},high:{fps:60,resolution:768,pixelRatio:1.5}});
export function performanceSettings(value='balanced'){
 const p=typeof value==='string'?PRESETS[value]:value;
 if(!p||![15,24,30,45,60].includes(p.fps)||![256,512,768].includes(p.resolution)||![.75,1,1.5].includes(p.pixelRatio))throw Error('Invalid performance settings');
 return {fps:p.fps,resolution:p.resolution,pixelRatio:p.pixelRatio};
}
export function summarizeObservation(frames,settings){
 settings=performanceSettings(settings);
 if(!Array.isArray(frames)||frames.length<20||frames.some(f=>!Number.isFinite(f.time)||!Number.isFinite(f.cost)||f.cost<0))throw Error('Observe at least 20 actual playback frames');
 const span=frames.at(-1).time-frames[0].time;if(span<=0)throw Error('Invalid observation span');
 const costs=frames.map(f=>f.cost).sort((a,b)=>a-b),fps=(frames.length-1)*1000/span,p95=costs[Math.ceil(costs.length*.95)-1];
 const slow=fps<settings.fps*.8||p95>1000/settings.fps*1.25;
 const recommendation=slow?(settings.resolution>256?'low':'low'):null;
 return {schema:'jali-playback-observation-v1',settings,frames:frames.length,span_ms:span,observed_fps:fps,p95_submission_or_native_response_ms:p95,recommended_preset:recommendation,limits:'Observed on this browser/device during playback; recommendation is a conservative heuristic, not GPU time, physical AV latency or a certified laptop preset.'};
}
