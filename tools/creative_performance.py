"""Native counterpart of bounded manual JS animation; parity tested numerically."""
import math
DEFAULTS=dict(natural=False,intensity=1,contact=1,head=1,blink=1,blinkRate=1,gazeEase=.35,gazeFrom='forward',gazeStart=0,seed=19,offset=0,idle=False,idleTime=0,sequence=[])
EXPRESSIONS=('neutral','warm','attentive','serious','surprise')
STYLES=dict(neutral={},warm=dict(mouthSmileLeft=.16,mouthSmileRight=.16,cheekSquintLeft=.06,cheekSquintRight=.06),attentive=dict(browInnerUp=.25,browOuterUpLeft=.12,browOuterUpRight=.12),serious=dict(browDownLeft=.3,browDownRight=.3,mouthFrownLeft=.12,mouthFrownRight=.12),surprise=dict(browInnerUp=.4,eyeWideLeft=.32,eyeWideRight=.32))
DIRECTIONS=dict(forward=(0,0),left=(.08,0),right=(-.08,0),down=(0,.06))
def finite(v,a,b):return type(v) in (int,float) and math.isfinite(v) and a<=v<=b

def settings(value=None):
    value={} if value is None else value
    if not isinstance(value,dict) or set(value)-set(DEFAULTS):raise ValueError('Unknown creative setting')
    p={**DEFAULTS,**value}
    for k,a,b in [('intensity',0,1),('contact',0,1),('head',0,1),('blink',0,1),('blinkRate',.25,2),('gazeEase',0,2),('gazeStart',0,3600),('seed',0,65535),('offset',0,60),('idleTime',0,3600)]:
        if not finite(p[k],a,b):raise ValueError('Invalid creative '+k)
    if int(p['seed'])!=p['seed'] or type(p['natural']) is not bool or type(p['idle']) is not bool or p['gazeFrom'] not in DIRECTIONS:raise ValueError('Invalid creative motion')
    if not isinstance(p['sequence'],list) or len(p['sequence'])>32:raise ValueError('Too many expression events')
    for e in p['sequence']:
        if not isinstance(e,dict) or set(e)!={'start','end','expression','intensity','fade'} or not finite(e['start'],0,60) or not finite(e['end'],0,60) or e['end']<=e['start'] or e['expression'] not in EXPRESSIONS or not finite(e['intensity'],0,1) or not finite(e['fade'],0,2) or e['fade']>(e['end']-e['start'])/2:raise ValueError('Invalid expression event')
    return p

def smooth(x):
    x=max(0,min(1,x));return x*x*(3-2*x)

def compose(weights,time,duration,life,mood,gaze,value=None):
    p=settings(value);pose=dict(weights);t=time+p['offset']
    if mood not in EXPRESSIONS or gaze not in DIRECTIONS or not math.isfinite(time) or not math.isfinite(duration) or any(not finite(v,0,1) for v in weights.values()):raise ValueError('Invalid manual performance')
    protected=min(1,max(weights.get('viseme_PP',0)/.95,weights.get('viseme_FF',0)/.85,weights.get('viseme_U',0)/.88,weights.get('viseme_O',0)/.65))
    def add(style,scale):
        for k,v in STYLES[style].items():
            protection=1-protected if k.startswith('mouth') or style=='warm' and k.startswith('cheek') else 1
            pose[k]=min(1,pose.get(k,0)+v*scale*protection)
    add(mood,p['intensity'])
    for e in p['sequence']:
        if not p['idle'] and e['start']<=t<e['end']:
            fade=min(smooth((t-e['start'])/e['fade']),smooth((e['end']-t)/e['fade'])) if e['fade'] else 1
            add(e['expression'],p['intensity']*e['intensity']*fade)
    active=life and (p['natural'] if p['idle'] else 0<time<duration);mt=p['idleTime'] if p['idle'] else t;yaw=roll=0
    if active:
        if p['natural']:
            bt=mt*p['blinkRate'];n=math.floor(bt/4);center=n*4+.8+((n*37+p['seed'])%101)/101*1.7
            blink=smooth(1-abs(bt-center)/.11)
            if n%5==3:blink=max(blink,smooth(1-abs(bt-center-.32)/.09))
            blink*=p['blink'];yaw=(math.sin(mt*.47)*.013+math.sin(mt*1.13+.8)*.005)*p['head'];roll=(math.sin(mt*.31)*.006+math.sin(mt*.83)*.002)*p['head']
        else:
            blink=max(0,1-abs((time+.7)%3.8-3.25)/.11)*p['blink'];yaw=math.sin(time*.73)*.018*p['head'];roll=math.sin(time*.51)*.008*p['head']
        pose['eyeBlinkLeft']=pose['eyeBlinkRight']=blink
    source=DIRECTIONS[p['gazeFrom']];target=DIRECTIONS[gaze];a=(smooth(((mt if p['idle'] else t)-p['gazeStart'])/p['gazeEase']) if p['gazeEase'] else 1) if p['natural'] else 1
    ey=source[0]+(target[0]-source[0])*a;ep=source[1]+(target[1]-source[1])*a
    if active and p['natural']:ey+=(1-p['contact'])*math.sin(mt*.61)*.055;ep+=(1-p['contact'])*math.sin(mt*.39+.3)*.02
    return pose,dict(head_yaw=yaw,head_roll=roll,eye_yaw=ey,eye_pitch=ep)
