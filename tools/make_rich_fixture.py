#!/usr/bin/env python3
"""Original tiny canonical GLB for model-free native morph/material/alpha tests."""
import json
from pathlib import Path
import struct
import sys
import zlib


def make(output):
    data=bytearray();views=[];accessors=[]
    def view(b):
        while len(data)%4:data.append(0)
        views.append({'buffer':0,'byteOffset':len(data),'byteLength':len(b)});data.extend(b);return len(views)-1
    def acc(v,t,kind='f'):
        components={'VEC2':2,'VEC3':3,'VEC4':4,'SCALAR':1,'MAT4':16}[t]
        a={'bufferView':view(struct.pack('<'+kind*len(v),*v)),'componentType':{'f':5126,'H':5123}[kind],'type':t,'count':len(v)//components}
        if t!='MAT4':views[a['bufferView']]['target']=34963 if t=='SCALAR' else 34962
        if t=='VEC3':a.update(min=[min(v[k::3]) for k in range(3)],max=[max(v[k::3]) for k in range(3)])
        accessors.append(a);return len(accessors)-1
    def png(rgba):
        def chunk(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
        return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0'+bytes(rgba)))+chunk(b'IEND',b'')
    attrs={'POSITION':acc([-.5,-.5,0,.5,-.5,0,0,.5,0],'VEC3'),'NORMAL':acc([0,0,1]*3,'VEC3'),'TEXCOORD_0':acc([0,0,1,0,.5,1],'VEC2'),'JOINTS_0':acc([0]*12,'VEC4','H'),'WEIGHTS_0':acc([1,0,0,0]*3,'VEC4')}
    targets=[{'POSITION':acc([0,v,0]*3,'VEC3'),'NORMAL':acc([v,0,0]*3,'VEC3')} for v in [.1,.2,.3]]
    indices=acc([0,1,2],'SCALAR','H');inverse=acc([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],'MAT4')
    color=[255,180,140,255];normal=[128,128,255,255];cv=view(png(color));nv=view(png(normal));raw=view(bytes(color));nraw=view(bytes(normal))
    materials=[{'pbrMetallicRoughness':{'baseColorTexture':{'index':0},'baseColorFactor':[1,1,1,1]},'alphaMode':mode} for mode in ['OPAQUE','BLEND']]
    model={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0,1]}],'nodes':[{'name':'Head'},{'name':'Mesh','mesh':0,'skin':0}],
        'skins':[{'joints':[0],'inverseBindMatrices':inverse}],'meshes':[{'extras':{'targetNames':['viseme_PP','viseme_aa','viseme_U']},'primitives':[{'mode':4,'attributes':attrs,'indices':indices,'targets':targets,'material':i} for i in range(2)]}],
        'materials':materials,'images':[{'bufferView':cv,'mimeType':'image/png'},{'bufferView':nv,'mimeType':'image/png'}],'textures':[{'source':0},{'source':1}],
        'extras':{'jaliNativeProfile':'rich-v1','source_sha256':'0'*64,'camera':[0,0,0,.8],'nativeAtlas':{'width':1,'height':1,'bufferView':raw,'normalBufferView':nraw}},
        'buffers':[{'byteLength':len(data)}],'bufferViews':views,'accessors':accessors}
    text=json.dumps(model,separators=(',',':')).encode();text+=b' '*((-len(text))%4);data+=b'\0'*((-len(data))%4)
    p=Path(output);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(struct.pack('<III',0x46546c67,2,28+len(text)+len(data))+struct.pack('<I4s',len(text),b'JSON')+text+struct.pack('<I4s',len(data),b'BIN\0')+data)


if __name__=='__main__':make(sys.argv[1])
