"""Example local-app client. No third-party packages, no credentials in arguments/logs."""
import argparse
import json
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlparse

def request(base,key,route,payload=None):
    parsed=urlparse(base)
    if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost','::1') or parsed.username or parsed.password:raise ValueError('Use a loopback HTTP studio URL')
    req=Request(base.rstrip('/')+route,data=None if payload is None else json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urlopen(req,timeout=10) as response:return json.load(response)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url',default='http://127.0.0.1:8082');p.add_argument('--key-file',type=Path,required=True);p.add_argument('command',choices=['submit','pause','resume','interrupt','expression','events','cast']);p.add_argument('--text');p.add_argument('--speaker',default='default');p.add_argument('--style',default='neutral');p.add_argument('--intensity',type=float,default=1);p.add_argument('--after',type=int,default=0);a=p.parse_args();key=a.key_file.read_text().strip()
    if a.command=='cast':result=request(a.url,key,'/api/integration/cast')
    elif a.command=='events':result=request(a.url,key,'/api/integration/events?after='+str(a.after))
    else:
        data={'type':a.command}
        if a.command=='submit':data.update(text=a.text,speaker=a.speaker)
        if a.command=='expression':data.update(expression=a.style,intensity=a.intensity)
        result=request(a.url,key,'/api/integration/commands',data)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
