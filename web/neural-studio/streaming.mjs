// Validate absolute integer PCM offsets; never infer ordering from arrival time.
export function validateStreamChunk(item,index,start,rate){
  if(!Number.isInteger(rate)||rate<16000||rate>48000||!item||item.index!==index||!Number.isInteger(item.start_sample)||!Number.isInteger(item.end_sample)||item.start_sample!==start||item.end_sample<=start||item.end_sample-start>rate*60||item.id!==item.clip?.id||item.clip.audio?.sample_rate!==rate||Math.abs(item.clip.duration*rate-(item.end_sample-start))>1)throw new Error('Invalid sentence-batch order, sample rate or PCM offsets');
  return item.end_sample;
}
