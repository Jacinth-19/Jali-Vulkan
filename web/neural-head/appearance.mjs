export const APPEARANCE_DEFAULTS={lighting:'studio',background:'slate',camera:'portrait',exposure:1.05,skin:.75,eyes:.12,fxaa:false};
export const BACKGROUNDS={slate:'#101a1d',charcoal:'#18181c',cream:'#d6cbbb',blue:'#203c56',green:'#24433b'};
export function appearanceSettings(value={}){
 if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).some(k=>!Object.hasOwn(APPEARANCE_DEFAULTS,k)))throw Error('Unknown appearance setting');
 const p={...APPEARANCE_DEFAULTS,...value};
 if(!['studio','soft','dramatic'].includes(p.lighting)||!Object.hasOwn(BACKGROUNDS,p.background)||!['portrait','close','threequarter','wide'].includes(p.camera)||typeof p.fxaa!=='boolean')throw Error('Unknown appearance preset');
 for(const [k,a,b] of [['exposure',.5,1.8],['skin',.3,1],['eyes',.03,.6]])if(typeof p[k]!=='number'||!Number.isFinite(p[k])||p[k]<a||p[k]>b)throw Error('Invalid appearance '+k);
 return p;
}
