// Browser-enforced exclusive ownership across tabs/windows of this origin/profile.
// No heartbeat/expiry: a slow/background tab cannot create split-brain owners.
export async function rendererLease(locks, state=()=>{},signal) {
 if(!locks?.request)throw Error('Exclusive renderer ownership needs current Chrome on localhost/HTTPS. No model was loaded.');
 state('waiting');
 let release,granted,rejected;
 const acquired=new Promise((resolve,reject)=>{granted=resolve;rejected=reject;});
 const held=new Promise(resolve=>{release=resolve;});
 locks.request('jali-character-renderer-v1',{mode:'exclusive',...(signal?{signal}:{})},async()=>{
  state('owned');granted(()=>{release();});await held;state('released');
 }).catch(error=>{state(error.name==='AbortError'?'cancelled':'failed');rejected(error);});
 return acquired;
}
