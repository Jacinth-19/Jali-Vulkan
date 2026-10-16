// Presentation calibration, not a change to the verified WAV/cue identity.
export const ARTICULATION = Object.freeze({
 baseline:{closure:1,contact:1,tongue:1,jaw:1,rounding:1,transition:35,smooth:false},
 clear:{closure:1.05,contact:1.1,tongue:1.12,jaw:1,rounding:1.05,transition:35,smooth:true},
 soft:{closure:1,contact:1,tongue:1,jaw:.9,rounding:.95,transition:50,smooth:true}
});
export const LIMITS={closure:[.75,1.15],contact:[.7,1.2],tongue:[.5,1.5],jaw:[.7,1.2],rounding:[.7,1.2],transition:[0,70]};
export function articulation(value='baseline'){
 if(typeof value==='string'&&!Object.prototype.hasOwnProperty.call(ARTICULATION,value))throw Error('Unknown articulation profile');
 const p=typeof value==='string'?ARTICULATION[value]:value;
 if(!p||typeof p!=='object'||Array.isArray(p))throw Error('Unknown articulation profile');
 if(Object.keys(p).some(k=>!Object.prototype.hasOwnProperty.call(LIMITS,k)&&k!=='smooth'))throw Error('Unknown articulation setting');
 const result={...ARTICULATION.baseline,...p};
 for(const [k,[lo,hi]] of Object.entries(LIMITS))if(typeof result[k]!=='number'||!Number.isFinite(result[k])||result[k]<lo||result[k]>hi)throw Error('Invalid articulation '+k);
 if(typeof result.smooth!=='boolean')throw Error('Invalid articulation smoothing');return result;
}
export function calibrated(weights,p){
 const result={...weights};
 for(const k of Object.keys(result)){
  const scale=k==='viseme_PP'?p.closure:k==='viseme_FF'?p.contact:['viseme_nn','viseme_DD'].includes(k)?p.tongue:k==='viseme_aa'?p.jaw:['viseme_U','viseme_O'].includes(k)?p.rounding:1;
  result[k]=Math.min(1,Math.max(0,result[k]*scale));
 }return result;
}
