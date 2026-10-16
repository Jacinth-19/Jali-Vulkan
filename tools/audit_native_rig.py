"""Static M4 gap audit, not a native renderer or proof of supported deformation."""
import hashlib
import json
from pathlib import Path
import struct
import re

ROOT=Path(__file__).resolve().parents[1]


def read_glb(path):
    data=Path(path).read_bytes()
    if len(data)<20 or data[:4]!=b'glTF' or struct.unpack_from('<II',data,4)!=(2,len(data)):
        raise ValueError('Invalid GLB header/version/length')
    size,kind=struct.unpack_from('<II',data,12)
    if kind!=0x4e4f534a or size>len(data)-20:
        raise ValueError('Invalid GLB JSON chunk')
    return json.loads(data[20:20+size])


def audit(path):
    m=read_glb(path)
    meshes=m.get('meshes',[]);skins=m.get('skins',[])
    counts={'meshes':len(meshes),'skins':len(skins),'materials':len(m.get('materials',[])),
        'images':len(m.get('images',[])),'nodes':len(m.get('nodes',[])),
        'max_skin_joints':max((len(s.get('joints',[])) for s in skins),default=0),
        'max_morph_targets':max((len(p.get('targets',[])) for mesh in meshes for p in mesh['primitives']),default=0)}
    header=(ROOT/'include/jali/character.hpp').read_text()
    joint_limit=int(re.search(r'kMaxCharacterJoints = (\d+)',header).group(1))
    node_limit=int(re.search(r'kMaxCharacterNodes = (\d+)',header).group(1))
    blocks=[]
    def block(condition,code,required):
        if condition:blocks.append({'code':code,'required_work':required})
    block(bool(m.get('extensionsRequired')),'required_extensions','Decode Meshopt and support quantized attributes or produce a validated native asset profile.')
    block(counts['meshes']!=1 or counts['skins']!=1,'multi_mesh_skin','Preserve all meshes/instances and skin bindings, including teeth/tongue.')
    block(counts['max_skin_joints']>joint_limit,'palette_limit','Expand importer, palette ABI, shader arrays, buffers and reference tests together; never truncate joints.')
    block(counts['materials']>0 or counts['images']>0,'materials_textures','Implement UV/image upload, materials, color spaces and the relevant alpha/normal paths.')
    block(any(len(p.get('targets',[]))!=3 for mesh in meshes for p in mesh['primitives']),'three_target_abi','Replace the three fixed deltas with named morph storage and retarget the shared speech session.')
    block(any(set(mesh.get('extras',{}).get('targetNames',[]))!={'jawOpen','mouthRound','mouthClose'} for mesh in meshes),'target_names','Preserve actual named visemes and bind matching targets on secondary meshes.')
    block(bool(m.get('animations')),'authored_tracks','Handle or explicitly exclude authored tracks in a reviewed native profile.')
    block(any(a['componentType'] not in (5126,5121,5123,5125) for a in m.get('accessors',[])),'accessor_types','Audit signed/quantized accessor decoding, normalization and bounds.')
    block(counts['nodes']>node_limit,'node_limit','Review node limits and full hierarchy handling.')
    return {'schema':'jali-native-rig-audit-v1','model_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        'native_importer_source_sha256':hashlib.sha256((ROOT/'src/character.cpp').read_bytes()).hexdigest(),
        'native_profile_header_sha256':hashlib.sha256(header.encode()).hexdigest(),
        'profile':f'existing vertex-color, one-mesh, {joint_limit}-joint, three-morph native profile',
        'static_status':'known_incompatible' if blocks else 'requires_native_validation',
        'counts':counts,'required_extensions':m.get('extensionsRequired',[]),
        'morph_names_by_mesh':[{'name':mesh.get('name',''),'targets':mesh.get('extras',{}).get('targetNames',[])} for mesh in meshes],
        'blockers':blocks,'native_rendering_performed':False,'assets_modified':False,
        'limits':'Partial metadata gap audit, not a complete importer validator, GPU deformation comparison or completed M4 port.'}
