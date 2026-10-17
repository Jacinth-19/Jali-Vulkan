#!/usr/bin/env python3
"""Explicit offline-build male MakeHuman variant; no Blender or runtime downloads.

Uses CC0 MPFB assets, not MPFB's GPL Python implementation. SciPy is build-only.
The existing CC0 TalkingHead character supplies the speech rig, outfit and hair.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA = 'af03a0f41f19806c717b0c832ddd6513b06fd6258228b5ab844e06792e2e72ac'
MPFB_COMMIT = 'f4f4f1ffa8203585730a7ce433b66738777ba168'
SOURCE_SHA = '63c645a2a863b9972e9a9c2ed576a1de4c390b8475508e1473e69c87a3ee299c'


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def canonical_map(obj, source_uv, source_positions):
    """Exact UV correspondence; resolve shared UVs by fitted rest-space distance."""
    import numpy as np
    from scipy.spatial import cKDTree
    vertices, uv, pairs = [], [], []
    for line in Path(obj).read_text().splitlines():
        a = line.split()
        if not a:
            continue
        if a[0] == 'v':
            vertices.append(list(map(float, a[1:4])))
        elif a[0] == 'vt':
            uv.append([float(a[1]), 1-float(a[2])])  # glTF V convention
        elif a[0] == 'f':
            pairs.extend((int(v.split('/')[0])-1, int(v.split('/')[1])-1) for v in a[1:])
    vertices, uv, pairs = np.array(vertices), np.array(uv), np.array(pairs)
    candidates = cKDTree(uv[pairs[:, 1]]).query_ball_point(source_uv, 1e-6)
    ids = [np.unique(pairs[c, 0]) for c in candidates]
    if any(len(c) == 0 for c in ids):
        raise ValueError('Canonical UV correspondence failed; refusing guessed topology')
    unique = np.array([len(c) == 1 for c in ids])
    first = np.array([c[0] for c in ids])
    fit = np.linalg.lstsq(np.c_[vertices[first[unique]], np.ones(unique.sum())], source_positions[unique], rcond=None)[0]
    predicted = np.c_[vertices, np.ones(len(vertices))] @ fit
    chosen = np.array([c[np.argmin(np.linalg.norm(predicted[c]-p, axis=1))] for c, p in zip(ids, source_positions)])
    return chosen, len(vertices), int((~unique).sum())


def prepare(output):
    import numpy as np
    from scipy.spatial import cKDTree
    from build_neural_head import prepare_model
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Choose an empty output directory; existing character packages are never overwritten')
    output.mkdir(parents=True, exist_ok=True)
    source = ROOT / '.cache/lipsync/mpfb.glb'
    if not source.is_file() or any(not (ROOT/f'.cache/lipsync/textures/{i}.png').is_file() for i in range(7)):
        prepare_model()
    if digest(source) != SOURCE_SHA:
        raise ValueError('Expected pinned CC0 TalkingHead MakeHuman source')
    cache = ROOT / '.cache/male-generation'
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / 'mpfb2-v2.0.15.tar.gz'
    if not archive.is_file():
        with urllib.request.urlopen('https://codeload.github.com/makehumancommunity/mpfb2/tar.gz/refs/tags/v2.0.15', timeout=120) as r:
            data = r.read(48*1024*1024+1)
        if len(data) > 48*1024*1024:
            raise ValueError('MPFB archive exceeds build budget')
        archive.write_bytes(data)
    if digest(archive) != ARCHIVE_SHA:
        raise ValueError('MPFB archive checksum mismatch')
    assets = cache / 'mpfb2-2.0.15'
    # Extract only CC0 data and its license, never execute addon code.
    with tarfile.open(archive) as tar:
        for m in tar.getmembers():
            if m.isfile() and (m.name.startswith('mpfb2-2.0.15/src/mpfb/data/3dobjs/') or m.name.startswith('mpfb2-2.0.15/src/mpfb/data/targets/macrodetails/') or m.name == 'mpfb2-2.0.15/LICENSE.ASSETS.md'):
                if '..' in Path(m.name).parts or m.name.startswith('/') or m.size > 8*1024*1024:
                    raise ValueError('Unsafe archive member')
                dest = cache / m.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(tar.extractfile(m).read())
    raw = source.read_bytes()
    n = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20+n])
    binary = bytearray(raw[28+n:])
    arrays, edited = {}, set()
    def acc(index):
        if index in arrays:
            return arrays[index]
        a = doc['accessors'][index]
        size = {'SCALAR':1, 'VEC2':2, 'VEC3':3, 'VEC4':4, 'MAT4':16}[a['type']]
        dtype = {5126:'<f4', 5125:'<u4', 5123:'<u2', 5121:'u1'}[a['componentType']]
        def view(index, offset, count, size, dtype):
            v = doc['bufferViews'][index]
            if v.get('buffer',0) or 'extensions' in v:
                raise ValueError('Expected pinned uncompressed source')
            return np.ndarray((count,size),dtype=dtype,buffer=binary,offset=v.get('byteOffset',0)+offset,strides=(v.get('byteStride',np.dtype(dtype).itemsize*size),np.dtype(dtype).itemsize)).copy()
        value = view(a['bufferView'],a.get('byteOffset',0),a['count'],size,dtype) if 'bufferView' in a else np.zeros((a['count'],size),dtype=dtype)
        if 'sparse' in a:
            sp=a['sparse'];ix=sp['indices'];vals=sp['values']
            ids=view(ix['bufferView'],ix.get('byteOffset',0),sp['count'],1,{5121:'u1',5123:'<u2',5125:'<u4'}[ix['componentType']]).ravel()
            value[ids]=view(vals['bufferView'],vals.get('byteOffset',0),sp['count'],size,dtype)
        arrays[index]=value
        return value
    def put(index, value):
        if not np.isfinite(value).all():
            raise ValueError('Nonfinite generated accessor')
        arrays[index]=value.astype(acc(index).dtype)
        edited.add(index)
    body = next(m for m in doc['meshes'] if m['name']=='base')['primitives'][0]
    p = acc(body['attributes']['POSITION']).copy()
    mapping, count, ambiguous = canonical_map(assets/'src/mpfb/data/3dobjs/base.obj', acc(body['attributes']['TEXCOORD_0']), p)
    delta = np.zeros((count,3))
    targets = []
    # Adult, average-muscle/weight gender difference. Keep the source's custom
    # identity, pose and ancestry rather than replacing it with a generic head.
    for prefix in ['african', 'asian', 'caucasian', 'universal']:
        weight = 1/3 if prefix != 'universal' else 1
        for sex, sign in [('male',1), ('female',-1)]:
            name = f'{prefix}-{sex}-young' + ('-averagemuscle-averageweight' if prefix=='universal' else '') + '.target.gz'
            f = assets/'src/mpfb/data/targets/macrodetails'/name
            for line in gzip.decompress(f.read_bytes()).decode().splitlines():
                a = line.split()
                if a and not a[0].startswith('#'):
                    delta[int(a[0])] += .1 * sign * weight * np.array(list(map(float,a[1:4])))
            targets.append({'file':name, 'sha256':digest(f), 'weight':sign*weight})
    displacement = delta[mapping]
    tree = cKDTree(p)
    def field(points):
        dist, ix = tree.query(points, k=12)
        w = 1/np.maximum(dist,1e-6)**2
        return (displacement[ix]*w[:,:,None]).sum(axis=1)/w.sum(axis=1)[:,None]
    # Gender targets change stature too. Refit every joint/rest inverse bind,
    # not just the vertices, or eyes and head animation would remain 13cm below
    # the new male face. Preserve authored rest orientations and skin correction.
    def local_matrix(node):
        if 'matrix' in node:return np.array(node['matrix']).reshape(4,4).T
        x,y,z,w=node.get('rotation',[0,0,0,1]);m=np.eye(4)
        m[:3,:3]=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]) @ np.diag(node.get('scale',[1,1,1]))
        m[:3,3]=node.get('translation',[0,0,0]);return m
    nodes=doc['nodes'];parents={child:i for i,node in enumerate(nodes) for child in node.get('children',[])}
    old_world={}
    def world(i):
        if i not in old_world:old_world[i]=(world(parents[i]) if i in parents else np.eye(4)) @ local_matrix(nodes[i])
        return old_world[i]
    for i in range(len(nodes)):world(i)
    for node in nodes:
        if 'mesh' in node and not np.allclose(world(nodes.index(node)),np.eye(4),atol=1e-6):raise ValueError('Expected world-space pinned meshes')
    joints=sorted({j for skin in doc['skins'] for j in skin['joints']})
    offsets={i:field(old_world[i][:3,3][None,:])[0] for i in joints}
    new_world={i:m.copy() for i,m in old_world.items()}
    for i,d in offsets.items():new_world[i][:3,3]+=d
    for i in joints:
        node=nodes[i]
        if 'matrix' in node:raise ValueError('Expected TRS bones in pinned source')
        parent=new_world[parents[i]] if i in parents else np.eye(4)
        node['translation']=(np.linalg.inv(parent) @ new_world[i][:,3])[:3].tolist()
    for skin in doc['skins']:
        index=skin['inverseBindMatrices'];matrices=acc(index).copy().reshape(-1,4,4).transpose(0,2,1)
        for k,j in enumerate(skin['joints']):matrices[k]=np.linalg.inv(new_world[j]) @ old_world[j] @ matrices[k]
        put(index,matrices.transpose(0,2,1).reshape(-1,16))
    eyes={nodes[i]['name']:offsets[i] for i in joints if nodes[i].get('name') in ('LeftEye','RightEye')}
    def normals(points, indices):
        tri = indices.reshape(-1,3)
        face = np.cross(points[tri[:,1]]-points[tri[:,0]], points[tri[:,2]]-points[tri[:,0]])
        normal = np.zeros_like(points)
        for j in range(3):
            np.add.at(normal,tri[:,j],face)
        return normal/np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-12)
    # Rigid eyeballs move with their refitted pivots without changing radius.
    # Adjacent lids/brows follow the full male head deformation.
    changes = []
    for mesh in doc['meshes']:
        for prim in mesh['primitives']:
            attrs = prim['attributes']
            old = acc(attrs['POSITION']).copy()
            rigid = mesh['name'] == 'high-poly'
            offset = np.where((old[:,0]>0)[:,None],eyes['LeftEye'],eyes['RightEye']) if rigid else field(old)
            new = old + offset
            indices = acc(prim['indices']).copy()
            normal = normals(new, indices)
            # Save morph deltas before changing any shared storage.
            for target in prim.get('targets',[]):
                d = acc(target['POSITION']).copy() if 'POSITION' in target else np.zeros_like(old)
                updated = d if rigid else d + field(old+d)-offset
                if 'POSITION' in target:
                    put(target['POSITION'], updated)
                if 'NORMAL' in target:
                    put(target['NORMAL'], normals(new+updated,indices)-normal)
            put(attrs['POSITION'], new)
            if 'NORMAL' in attrs:
                put(attrs['NORMAL'],normal)
            changes.append({'mesh':mesh['name'], 'max_displacement_m':float(np.linalg.norm(offset,axis=1).max())})
    for index in sorted(edited):
        value=arrays[index]
        binary += b'\0' * (-len(binary)%4)
        meta=doc['accessors'][index]
        meta.pop('sparse',None);meta.pop('byteOffset',None)
        meta['bufferView']=len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':value.nbytes})
        binary.extend(value.tobytes())
        for key,fn in [('min',np.min),('max',np.max)]:
            if key in meta:meta[key]=fn(value,axis=0).tolist()
    doc['buffers'][0]['byteLength']=len(binary)
    encoded = json.dumps(doc,separators=(',',':')).encode()
    encoded += b' ' * (-len(encoded)%4)
    binary += b'\0' * (-len(binary)%4)
    result = struct.pack('<III',0x46546c67,2,28+len(encoded)+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(binary),0x004e4942)+binary
    generated = output/'male-source.glb'
    generated.write_bytes(result)
    shutil.copy2(assets/'LICENSE.ASSETS.md',output/'MPFB-ASSETS-CC0.md')
    evidence = {'schema':'jali-makehuman-male-v1','source_sha256':SOURCE_SHA,'mpfb_commit':MPFB_COMMIT,'mpfb_archive_sha256':ARCHIVE_SHA,'targets':targets,'uv_matched_vertices':len(mapping),'uv_shared_resolved_vertices':ambiguous,'uv_tolerance':1e-6,'scale_to_metres':.1,'changes':changes,'bone_rest_offsets_m':{nodes[i].get('name',str(i)):d.tolist() for i,d in offsets.items()},'method':'Official adult male-minus-female macro targets, ancestry-averaged, exact canonical UV correspondence; smooth spatial transfer to attachments and facial morphs; recomputed rest/morph normals. Spherical eyes translated rigidly with refitted pivots; all joint positions and inverse binds refitted, rest orientations retained. Shared ponytail and outfit. Not a new independently authored male scan.','epic_metahuman':False,'public_redistribution_approved':False}
    (output/'male-source.json').write_text(json.dumps(evidence,indent=2)+'\n')
    subprocess.run(['node','tools/prepare_makehuman_male.mjs',str(output)],cwd=ROOT,check=True,timeout=120)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/male-character')
    print(prepare(parser.parse_args().output))
