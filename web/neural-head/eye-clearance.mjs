// Explicit companion geometry, present only in enhanced WebGL assets. Original
// controls stay bounded to 0..1; no hidden >1 blink extrapolation or eye hiding.
export const EYE_SEAL_NAMES=['jaliEyeSealLeft','jaliEyeSealRight'];
export function eyeClearancePose(pose,supported=false){
 if(!supported)return pose;
 const result={...pose};
 for(const [i,side] of ['Left','Right'].entries()){
  const v=pose['eyeBlink'+side]??0;if(!Number.isFinite(v)||v<0||v>1)throw Error('Invalid blink control');
  const t=Math.max(0,Math.min(1,(v-.7)/.3));result[EYE_SEAL_NAMES[i]]=t*t*(3-2*t);
 }
 return result;
}
