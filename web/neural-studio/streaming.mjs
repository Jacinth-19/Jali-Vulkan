// Validate absolute integer PCM offsets; never infer ordering from arrival time.
export function validateStreamChunk(item,index,start,rate){
  if(!Number.isInteger(rate)||rate<16000||rate>48000||!item||item.index!==index||!Number.isInteger(item.start_sample)||!Number.isInteger(item.end_sample)||item.start_sample!==start||item.end_sample<=start||item.end_sample-start>rate*60||item.id!==item.clip?.id||item.clip.audio?.sample_rate!==rate||Math.abs(item.clip.duration*rate-(item.end_sample-start))>1)throw new Error('Invalid sentence-batch order, sample rate or PCM offsets');
  return item.end_sample;
}

// At most two verified, decoded audio chunks. Owns and releases every prefetch;
// a late download after Stop must not leak a URL or become the next performance.
export class AudioPrefetch {
 constructor(prepare,dispose){this.prepare=prepare;this.dispose=dispose;this.entries=new Map();this.closed=false;this.hits=0;}
 add(item){
  if(this.closed)throw new Error('Prefetch closed');
  if(this.entries.has(item.index))return;
  if(this.entries.size>=2)throw new Error('Prefetch queue budget exceeded');
  const controller=new AbortController(),entry={id:item.id,controller,value:null,error:null};
  entry.promise=Promise.resolve().then(()=>this.prepare(item,controller.signal)).then(value=>{if(this.closed||controller.signal.aborted){this.dispose(value);return null;}entry.value=value;return value;},error=>{entry.error=error;return null;});
  this.entries.set(item.index,entry);
 }
 async take(item){
  if(!this.entries.has(item.index))this.add(item);
  const entry=this.entries.get(item.index);if(entry.id!==item.id)throw new Error('Prefetched sentence identity changed');
  if(entry.value)this.hits++;
  const value=await entry.promise;this.entries.delete(item.index);
  if(entry.error)throw entry.error;
  if(!value||this.closed)throw new DOMException('Playback cancelled','AbortError');
  return value;
 }
 close(){if(this.closed)return;this.closed=true;for(const e of this.entries.values()){e.controller.abort();if(e.value)this.dispose(e.value);}this.entries.clear();}
}
