#!/usr/bin/env python3
"""Offline decoded native GLB profile: all meshes, named morphs and textured PBR.

Textures are packed losslessly into one padded sRGB atlas; the GLB also embeds
bounded raw RGBA for native upload without a runtime image-codec dependency.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def build(source,output):
    output.mkdir(parents=True,exist_ok=True);temp=output/'intermediate'
    subprocess.run(['node','tools/prepare_native_head.cjs',str(source),str(temp)],cwd=ROOT,check=True,timeout=120)
    meta=json.loads((temp/'metadata.json').read_text());raw=(temp/'geometry.bin').read_bytes()
    def unpack(ref,kind='f'):
        return list(struct.unpack('<'+kind*(ref['length']//4),raw[ref['offset']:ref['offset']+ref['length']]))
    textures=sorted({m[k] for m in meta['materials'] for k in ('texture','normal') if m[k]>=0})
    images={i:Image.open(temp/f'texture-{i}.bin').convert('RGBA') for i in textures}
    if any(max(im.size)>1024 for im in images.values()):raise ValueError('Texture exceeds prepared 1024px limit')
    tile=1028;columns=3;rows=max(1,(len(meta['materials'])+2)//3)
    if rows>3:raise ValueError('Native atlas exceeds nine textures')
    atlas=Image.new('RGBA',(columns*tile,rows*tile),(255,255,255,255));rects={}
    normal_atlas=Image.new('RGBA',atlas.size,(128,128,255,255))
    def padded(image,wrap_s,wrap_t):
        w,h=image.size;out=Image.new('RGBA',(w+4,h+4));out.paste(image,(2,2))
        def coord(k,n,mode):
            if mode==10497:return k%n
            if mode==33648:
                i=k%(2*n);return i if i<n else 2*n-1-i
            if mode==33071:return max(0,min(n-1,k))
            raise ValueError('Unsupported texture wrapping')
        for y in range(-2,h+2):
            for x in (range(-2,w+2) if y<0 or y>=h else (-2,-1,w,w+1)):
                out.putpixel((x+2,y+2),image.getpixel((coord(x,w,wrap_s),coord(y,h,wrap_t))))
        return out
    for index,m in enumerate(meta['materials']):
        im=images[m['texture']] if m['texture']>=0 else Image.new('RGBA',images[m['normal']].size if m['normal']>=0 else (1,1),(255,255,255,255))
        x=(index%columns)*tile+2;y=(index//columns)*tile+2;w,h=im.size
        atlas.paste(padded(im,m['wrapS'],m['wrapT']),(x-2,y-2));rects[index]=(x,y,w,h)
        if m['normal']>=0:
            normal=images[m['normal']]
            if normal.size!=(w,h):raise ValueError('Canonical paired atlas requires equal diffuse/normal dimensions; resample explicitly upstream')
            normal_atlas.paste(padded(normal,m['normalWrapS'],m['normalWrapT']),(x-2,y-2))
    data=bytearray();views=[];accessors=[]
    def view(blob):
        while len(data)%4:data.append(0)
        r=len(views);views.append({'buffer':0,'byteOffset':len(data),'byteLength':len(blob)});data.extend(blob);return r
    def acc(values,shape,kind='f'):
        count={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[shape]
        a={'bufferView':view(struct.pack('<'+kind*len(values),*values)),'componentType':{'f':5126,'I':5125,'H':5123}[kind],'count':len(values)//count,'type':shape}
        if shape!='MAT4':views[a['bufferView']]['target']=34963 if shape=='SCALAR' else 34962
        if shape=='VEC3':a.update(min=[min(values[k::3]) for k in range(3)],max=[max(values[k::3]) for k in range(3)])
        accessors.append(a);return len(accessors)-1
    primitives=[]
    for p in meta['primitives']:
        n=p['count'];uv=unpack(p['uv']);m=meta['materials'][p['material']]
        if m['texture']>=0 or m['normal']>=0:
            x,y,w,h=rects[p['material']]
            for i in range(n):
                u,v=uv[i*2:i*2+2]
                if not -.0001<=u<=1.0001 or not -.0001<=v<=1.0001:raise ValueError('Atlas profile requires non-repeating UVs')
                uv[i*2]=(x+max(0,min(1,u))*w)/atlas.width;uv[i*2+1]=(y+max(0,min(1,v))*h)/atlas.height
        else:uv=[.5/atlas.width,.5/atlas.height]*n
        attrs={'POSITION':acc(unpack(p['positions']),'VEC3'),'NORMAL':acc(unpack(p['normals']),'VEC3'),
            'TEXCOORD_0':acc(uv,'VEC2'),'JOINTS_0':acc(unpack(p['joints'],'I'),'VEC4','H'),'WEIGHTS_0':acc(unpack(p['weights']),'VEC4')}
        targets=[]
        for name in meta['targetNames']:
            t=p['targets'].get(name,{})
            targets.append({key:acc(unpack(t[field]) if t.get(field) else [0.]*(n*3),'VEC3') for key,field in [('POSITION','position'),('NORMAL','normal')]})
        primitives.append({'mode':4,'attributes':attrs,'indices':acc(unpack(p['indices'],'I'),'SCALAR','I'),'targets':targets,'material':p['material'],'extras':{'sourceMesh':p['name']}})
    nodes=[]
    for j in meta['joints']:nodes.append({'name':j['name'],'matrix':j['local']})
    roots=[]
    for i,j in enumerate(meta['joints']):
        if j['parent']<0:roots.append(i)
        else:nodes[j['parent']].setdefault('children',[]).append(i)
    nodes.append({'name':'All original mesh instances','mesh':0,'skin':0});roots.append(len(nodes)-1)
    ibm=acc([v for j in meta['joints'] for v in j['inverse']],'MAT4')
    png=io.BytesIO();atlas.save(png,format='PNG',optimize=True);pngview=view(png.getvalue());atlasview=view(atlas.tobytes());normalview=view(normal_atlas.tobytes())
    npng=io.BytesIO();normal_atlas.save(npng,format='PNG',optimize=True);normalpngview=view(npng.getvalue())
    materials=[{'name':m['name'],'pbrMetallicRoughness':{'baseColorFactor':m['factor'],'metallicFactor':m['metallic'],'roughnessFactor':m['roughness'],'baseColorTexture':{'index':0}},'alphaMode':m['alphaMode'],'alphaCutoff':m['alphaCutoff'],'doubleSided':m['doubleSided']} for m in meta['materials']]
    for m,original in zip(materials,meta['materials']):
        if m['alphaMode']!='MASK':m.pop('alphaCutoff',None)
        if original['normal']>=0:m['normalTexture']={'index':1,'scale':original['normalScale']}
    model={'asset':{'version':'2.0','generator':'Jali native canonical profile v1'},'scene':0,'scenes':[{'nodes':roots}],
        'extras':{'jaliNativeProfile':'rich-v1','source_sha256':meta['source_sha256'],'camera':meta['camera'],'nativeAtlas':{'width':atlas.width,'height':atlas.height,'bufferView':atlasview,'normalBufferView':normalview}},
        'nodes':nodes,'skins':[{'joints':list(range(len(meta['joints']))),'inverseBindMatrices':ibm}],
        'meshes':[{'name':'Preserved original primitive groups','extras':{'targetNames':meta['targetNames']},'primitives':primitives}],
        'materials':materials,'images':[{'bufferView':pngview,'mimeType':'image/png'},{'bufferView':normalpngview,'mimeType':'image/png'}],'textures':[{'source':0},{'source':1}],
        'bufferViews':views,'accessors':accessors,'buffers':[{'byteLength':len(data)}]}
    js=json.dumps(model,separators=(',',':')).encode();js+=b' '*((-len(js))%4);data+=b'\0'*((-len(data))%4)
    target=output/'mpfb-native.glb';target.write_bytes(struct.pack('<III',0x46546c67,2,28+len(js)+len(data))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(data),b'BIN\0')+data)
    summary={'schema':'jali-native-head-profile-v1','source_sha256':meta['source_sha256'],'native_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'meshes_preserved_as_primitive_groups':len(primitives),'vertices':sum(p['count'] for p in meta['primitives']),
        'palette_nodes':len(nodes)-1,'named_targets':len(meta['targetNames']),'materials':len(materials),'atlas_size':list(atlas.size),
        'limits':'Offline decoded profile, base-color/normal/alpha/metallic/roughness PBR. Emissive/occlusion/metallic-roughness maps and inconsistent non-common inverse binds fail explicitly; no runtime Meshopt decoder.'}
    (output/'profile.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));return target


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'artifacts/neural-head-demo/model/mpfb-head.glb');p.add_argument('--output',type=Path,default=ROOT/'artifacts/native-head');a=p.parse_args();build(a.source.resolve(),a.output.resolve())
