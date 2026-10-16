// Bounded, deterministic manual animation. No emotion inference or tracking.
export const EXPRESSIONS=['neutral','warm','attentive','serious','surprise'];
const finite=(v,a,b)=>typeof v==='number'&&Number.isFinite(v)&&v>=a&&v<=b;
export const smooth=x=>{x=Math.max(0,Math.min(1,x));return x*x*(3-2*x);};
export const CREATIVE_DEFAULTS={natural:false,intensity:1,contact:1,head:1,blink:1,blinkRate:1,gazeEase:.35,gazeFrom:'forward',gazeStart:0,seed:19,offset:0,idle:false,idleTime:0,sequence:[]};
export function creativeSettings(value={}){
 if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).some(k=>!Object.hasOwn(CREATIVE_DEFAULTS,k)))throw Error('Unknown creative setting');
 const p={...CREATIVE_DEFAULTS,...value};
 for(const [k,a,b] of [['intensity',0,1],['contact',0,1],['head',0,1],['blink',0,1],['blinkRate',.25,2],['gazeEase',0,2],['gazeStart',0,3600],['seed',0,65535],['offset',0,60],['idleTime',0,3600]])if(!finite(p[k],a,b))throw Error('Invalid creative '+k);
 if(!Number.isInteger(p.seed)||typeof p.natural!=='boolean'||typeof p.idle!=='boolean'||!['forward','left','right','down'].includes(p.gazeFrom))throw Error('Invalid creative motion');
 if(!Array.isArray(p.sequence)||p.sequence.length>32)throw Error('Use at most 32 expression events');
 p.sequence=p.sequence.map(e=>{if(!e||typeof e!=='object'||Object.keys(e).some(k=>!['start','end','expression','intensity','fade'].includes(k))||!finite(e.start,0,60)||!finite(e.end,0,60)||e.end<=e.start||!EXPRESSIONS.includes(e.expression)||!finite(e.intensity,0,1)||!finite(e.fade,0,2)||e.fade>(e.end-e.start)/2)throw Error('Invalid timed expression (0–60 s, fade <= half its duration)');return {...e};});
 return p;
}
const directions={forward:[0,0],left:[.08,0],right:[-.08,0],down:[0,.06]};
const styles={neutral:{},warm:{mouthSmileLeft:.16,mouthSmileRight:.16,cheekSquintLeft:.06,cheekSquintRight:.06},attentive:{browInnerUp:.25,browOuterUpLeft:.12,browOuterUpRight:.12},serious:{browDownLeft:.3,browDownRight:.3,mouthFrownLeft:.12,mouthFrownRight:.12},surprise:{browInnerUp:.4,eyeWideLeft:.32,eyeWideRight:.32}};
export function creativePerformance(weights,{time=0,duration=0,life=false,mood='neutral',gaze='forward'}={},value={}){
 const p=creativeSettings(value),pose={...weights},t=time+p.offset;
 if(!EXPRESSIONS.includes(mood)||!Object.hasOwn(directions,gaze)||!Number.isFinite(time)||!Number.isFinite(duration)||Object.values(weights).some(v=>!finite(v,0,1)))throw Error('Invalid manual performance');
 const protectedMouth=Math.min(1,Math.max((weights.viseme_PP||0)/.95,(weights.viseme_FF||0)/.85,(weights.viseme_U||0)/.88,(weights.viseme_O||0)/.65));
 const add=(style,scale)=>{for(const [k,v] of Object.entries(styles[style])){const protection=k.startsWith('mouth')||(style==='warm'&&k.startsWith('cheek'))?1-protectedMouth:1;pose[k]=Math.min(1,(pose[k]||0)+v*scale*protection);}};
 add(mood,p.intensity);
 for(const e of p.sequence)if(!p.idle&&t>=e.start&&t<e.end){const f=e.fade?Math.min(smooth((t-e.start)/e.fade),smooth((e.end-t)/e.fade)):1;add(e.expression,p.intensity*e.intensity*f);}
 const active=life&&(p.idle?p.natural:(time>0&&time<duration)),mt=p.idle?p.idleTime:t;
 let yaw=0,roll=0,blink=0;
 if(active){
  if(p.natural){const bt=mt*p.blinkRate,n=Math.floor(bt/4),center=n*4+.8+((n*37+p.seed)%101)/101*1.7;
   blink=smooth(1-Math.abs(bt-center)/.11);if(n%5===3)blink=Math.max(blink,smooth(1-Math.abs(bt-center-.32)/.09));blink*=p.blink;
   yaw=(Math.sin(mt*.47)*.013+Math.sin(mt*1.13+.8)*.005)*p.head;roll=(Math.sin(mt*.31)*.006+Math.sin(mt*.83)*.002)*p.head;
  }else{blink=Math.max(0,1-Math.abs((time+.7)%3.8-3.25)/.11)*p.blink;yaw=Math.sin(time*.73)*.018*p.head;roll=Math.sin(time*.51)*.008*p.head;}
  pose.eyeBlinkLeft=pose.eyeBlinkRight=blink;
 }
 const from=directions[p.gazeFrom],to=directions[gaze],a=p.natural?(p.gazeEase?smooth(((p.idle?mt:t)-p.gazeStart)/p.gazeEase):1):1;
 let eyeYaw=from[0]+(to[0]-from[0])*a,eyePitch=from[1]+(to[1]-from[1])*a;
 if(active&&p.natural){eyeYaw+=(1-p.contact)*Math.sin(mt*.61)*.055;eyePitch+=(1-p.contact)*Math.sin(mt*.39+.3)*.02;}
 return {pose,head:{yaw,roll},eyes:{yaw:eyeYaw,pitch:eyePitch}};
}
