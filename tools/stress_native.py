#!/usr/bin/env python3
"""Bounded native-pipe longevity/RSS regression, NOT real-time or physical AV proof."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time
from rich_worker import RichWorker
from render_session import ROOT
from neural_visemes import shared_shapes
from make_rich_fixture import make


def resident_bytes(pid):
    if os.name!='nt':return int(Path(f'/proc/{pid}/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
    from ctypes import wintypes as w
    class Counters(ctypes.Structure):
        _fields_=[('cb',w.DWORD),('PageFaultCount',w.DWORD)]+[(n,ctypes.c_size_t) for n in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    k=ctypes.WinDLL('kernel32',use_last_error=True);ps=ctypes.WinDLL('psapi',use_last_error=True)
    k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE;k.CloseHandle.argtypes=[w.HANDLE]
    ps.GetProcessMemoryInfo.argtypes=[w.HANDLE,ctypes.POINTER(Counters),w.DWORD];ps.GetProcessMemoryInfo.restype=w.BOOL
    handle=k.OpenProcess(0x410,False,pid)
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    try:
        c=Counters();c.cb=ctypes.sizeof(c)
        if not ps.GetProcessMemoryInfo(handle,ctypes.byref(c),c.cb):raise ctypes.WinError(ctypes.get_last_error())
        return c.WorkingSetSize
    finally:k.CloseHandle(handle)


def exercise(asset,output,poses,count,size,software):
    worker=RichWorker(asset,output,software,size=size);timings=[];memory=[];hashes={};began=time.monotonic()
    try:
        # Touch every tested pose before comparing resident working-set growth.
        for pose in poses:
            raw,_=worker.frame(pose);hashes[json.dumps(pose,sort_keys=True)]=hashlib.sha256(raw).hexdigest()
        baseline=resident_bytes(worker.process.pid)
        for i in range(count):
            pose=poses[i%len(poses)];raw,ms=worker.frame(pose);timings.append(ms)
            if len(raw)!=size*size*4 or hashlib.sha256(raw).hexdigest()!=hashes[json.dumps(pose,sort_keys=True)]:raise AssertionError('Unstable/truncated binary frame on repeated identical pose')
            if (i+1)%250==0 or i==count-1:memory.append({'frame':i+1,'resident_bytes':resident_bytes(worker.process.pid)})
        growth=max(m['resident_bytes'] for m in memory)-baseline;budget=max(64*1024*1024,baseline//5)
        if growth>budget:raise AssertionError(f'Native resident growth {growth} exceeds regression budget {budget}')
        return {'renderer':worker.metadata,'frames_after_warmup':count,'size':size,'elapsed_seconds':time.monotonic()-began,'readback_ms_median':statistics.median(timings),'readback_ms_p95':sorted(timings)[int((len(timings)-1)*.95)],'resident_baseline_bytes':baseline,'resident_samples':memory,'maximum_resident_growth_bytes':growth,'regression_growth_budget_bytes':budget,'stable_pose_hashes':hashes}
    finally:worker.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--software-vulkan',action='store_true');p.add_argument('--output',type=Path,default=ROOT/'artifacts/native-stress');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    fixture=a.output/'fixture.glb';make(fixture)
    binary=ROOT/('build-live/jali_rich.exe' if os.name=='nt' else 'build-live/jali_rich')
    from render_session import runtime_environment
    parser_checks=[]
    for name,payload,code,frame_bytes in [('oversize-command',b' '*16385+b'\n',1,0),('windows-crlf-quit',b'quit\r\n',0,0),('last-command-without-newline',b'{}',0,64*64*4)]:
        result=subprocess.run([str(binary),'--asset',str(fixture),'--output',str(a.output/'parser'),'--size','64'],input=payload,capture_output=True,env=runtime_environment(a.software_vulkan),timeout=60)
        header,delimiter,raw=result.stdout.partition(b'\n')
        if result.returncode!=code or not delimiter or len(raw)!=frame_bytes or (code and b'16384' not in result.stderr):raise AssertionError(f'Native parser regression: {name}: {result.stderr!r}')
        json.loads(header);parser_checks.append({'case':name,'exit_code':result.returncode,'raw_frame_bytes':len(raw)})
    protocol=exercise(fixture,a.output/'protocol',[{}, {'viseme_PP':.95},{'viseme_aa':.88},{'viseme_U':.88}],10020,64,a.software_vulkan)
    rich=exercise(ROOT/'artifacts/native-head/mpfb-native.glb',a.output/'detailed',[v['weights'] for v in shared_shapes().values()],256,256,a.software_vulkan)
    evidence={'schema':'jali-native-longevity-v1','parser_checks':parser_checks,'protocol':protocol,'detailed_head':rich,'passed':True,'limits':'Regression budget, not a consumer memory/performance promise. Synthetic repeated poses, not sustained physical audio playback, gapless streaming or articulation approval.'}
    (a.output/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence,indent=2))


if __name__=='__main__':main()
