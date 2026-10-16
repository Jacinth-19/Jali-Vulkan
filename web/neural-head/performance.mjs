// Deterministic manual/cosmetic layers; no inferred emotion or gaze tracking.
// Speech owns the mouth: suppress warmth at full closures, F/V and rounding.
export function composePerformance(weights, {time=0, duration=0, life=false, mood='neutral', gaze='forward'}={}) {
  if (!Number.isFinite(time) || !Number.isFinite(duration) || duration<0) throw new Error('Invalid performance clock');
  if (!['neutral','warm','attentive'].includes(mood) || !['forward','left','right','down'].includes(gaze)) throw new Error('Unknown manual style or gaze');
  if (Object.values(weights).some(v=>!Number.isFinite(v)||v<0||v>1)) throw new Error('Invalid speech weight');
  const pose={...weights}, active=life && time>0 && time<duration;
  const protectedMouth=Math.min(1,Math.max((weights.viseme_PP||0)/.95,(weights.viseme_FF||0)/.85,(weights.viseme_U||0)/.88,(weights.viseme_O||0)/.65));
  if (mood==='warm') {
    pose.mouthSmileLeft=pose.mouthSmileRight=.16*(1-protectedMouth);
    pose.cheekSquintLeft=pose.cheekSquintRight=.06*(1-protectedMouth);
  }
  if (mood==='attentive') {pose.browInnerUp=.25;pose.browOuterUpLeft=pose.browOuterUpRight=.12;}
  if (active) {
    const blink=Math.max(0,1-Math.abs((time+.7)%3.8-3.25)/.11);
    pose.eyeBlinkLeft=pose.eyeBlinkRight=blink;
  }
  return {pose,head:{yaw:active?Math.sin(time*.73)*.018:0,roll:active?Math.sin(time*.51)*.008:0},
    eyes:{yaw:gaze==='left'?.08:gaze==='right'?-.08:0,pitch:gaze==='down'?.06:0}};
}
