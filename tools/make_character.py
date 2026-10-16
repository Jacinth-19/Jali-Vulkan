#!/usr/bin/env python3
"""Author an original self-contained glTF 2.0 GLB skin/morph fixture (no external art)."""
import json
import math
from pathlib import Path
import struct
import sys


def make_character(output, joint_count=2):
    if not 2 <= joint_count <= 128: raise ValueError("Fixture joint count must be 2-128")
    vertices, normals, colors, joints, weights, indices = [], [], [], [], [], []
    morphs = [[], [], []]
    def ellipsoid(center, radius, color, bone=0, mouth=False, segments=24, rings=16):
        base = len(vertices)
        for y in range(rings + 1):
            theta = math.pi * y / rings
            for x in range(segments + 1):
                phi = 2 * math.pi * x / segments
                unit = (math.sin(theta)*math.cos(phi), math.cos(theta), math.sin(theta)*math.sin(phi))
                local = tuple(unit[k]*radius[k] for k in range(3))
                vertices.append(tuple(center[k]+local[k] for k in range(3)))
                normal = tuple(unit[k]/radius[k] for k in range(3))
                length = math.sqrt(sum(v*v for v in normal))
                normals.append(tuple(v/length for v in normal)); colors.append(color)
                joints.append((bone, 0, 0, 0))
                jaw_weight = max(0.1, min(1, 0.65 - 0.5*unit[1])) if bone == 1 else 1
                weights.append((jaw_weight, 1-jaw_weight, 0, 0))
                morphs[0].append((0, unit[1]*0.075, 0) if mouth else (0, 0, 0))
                morphs[1].append((-local[0]*0.35, unit[1]*0.015, 0.006) if mouth else (0, 0, 0))
                morphs[2].append((0, -local[1]*0.8, 0) if mouth else (0, 0, 0))
        for y in range(rings):
            for x in range(segments):
                a = base+y*(segments+1)+x; b = a+segments+1
                indices.extend((a, b, a+1, b, b+1, a+1))
    shell, metal, trim, cyan = (.62,.68,.72), (.025,.043,.065), (.12,.21,.26), (.02,.85,1)
    ellipsoid((0,.16,0),(.61,.87,.52),shell,segments=48,rings=32)
    ellipsoid((0,-.54,.015),(.46,.34,.45),(.48,.55,.61),bone=1)
    ellipsoid((0,-1.02,-.06),(.24,.42,.25),metal)
    ellipsoid((0,-1.48,-.15),(1.18,.38,.44),metal)
    ellipsoid((0,-1.13,.04),(.40,.12,.35),trim)
    for s in (-1, 1):
        ellipsoid((s*.61,.13,-.04),(.105,.27,.16),metal)
        ellipsoid((s*.66,.13,.045),(.04,.18,.13),cyan)
        ellipsoid((s*.25,.29,.445),(.19,.085,.075),metal)
        ellipsoid((s*.25,.29,.495),(.139,.038,.041),cyan)
        ellipsoid((s*.25,.29,.532),(.022,.036,.008),metal)
        ellipsoid((s*.25,.40,.43),(.21,.035,.065),trim)
        ellipsoid((s*.38,-.13,.40),(.10,.17,.09),trim)
    ellipsoid((0,.10,.49),(.075,.205,.1),shell)
    ellipsoid((0,-.02,.55),(.095,.075,.07),shell)
    ellipsoid((0,-.32,.43),(.205,.04,.081),trim,mouth=True)
    ellipsoid((0,-.32,.493),(.173,.014,.028),(.006,.012,.025),mouth=True)
    ellipsoid((0,.72,.37),(.025,.17,.025),cyan)
    if joint_count > 2:
        for i in range(min(100,len(joints))):
            joints[i]=(joint_count-1,0,0,0);weights[i]=(1,0,0,0)
    data = bytearray(); views = []; accessors = []
    def accessor(values, component, shape, minimum=None, maximum=None, target=34962):
        while len(data) % 4: data.append(0)
        start = len(data)
        flat = [v for row in values for v in row]
        data.extend(struct.pack('<'+{'f': 'f', 'H': 'H', 'I': 'I'}[component]*len(flat), *flat))
        view={'buffer':0,'byteOffset':start,'byteLength':len(data)-start}
        if target is not None: view['target']=target
        views.append(view)
        a = {'bufferView':len(views)-1,'componentType':{'f':5126,'H':5123,'I':5125}[component],
             'count':len(values),'type':shape}
        if minimum is not None: a['min'] = minimum
        if maximum is not None: a['max'] = maximum
        accessors.append(a); return len(accessors)-1
    pos = accessor(vertices,'f','VEC3',[min(v[k] for v in vertices) for k in range(3)],[max(v[k] for v in vertices) for k in range(3)])
    normal = accessor(normals,'f','VEC3'); color = accessor(colors,'f','VEC3')
    joint = accessor(joints,'H','VEC4'); weight = accessor(weights,'f','VEC4')
    idx = accessor([(i,) for i in indices],'I','SCALAR',target=34963)
    targets = [{'POSITION':accessor(m,'f','VEC3',[min(v[k] for v in m) for k in range(3)],[max(v[k] for v in m) for k in range(3)])} for m in morphs]
    identity = [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
    jaw_inverse = identity.copy(); jaw_inverse[13] = .3
    ibm = accessor([identity,jaw_inverse]+[identity]*(joint_count-2),'f','MAT4',target=None)
    model = {'asset':{'version':'2.0','generator':'Jali original authored test character'},
             'scene':0,'scenes':[{'nodes':[0,2]}],
             'nodes':[{'name':'Root','children':[1]}, {'name':'Jaw','translation':[0,-.3,0]}, {'name':'Android','mesh':0,'skin':0}],
             'skins':[{'joints':[0,1],'inverseBindMatrices':ibm,'skeleton':0}],
             'meshes':[{'name':'Jali Android','weights':[0,0,0], 'extras':{'targetNames':['jawOpen','mouthRound','mouthClose']},
                        'primitives':[{'mode':4,'attributes':{'POSITION':pos,'NORMAL':normal,'COLOR_0':color,'JOINTS_0':joint,'WEIGHTS_0':weight},'indices':idx,'targets':targets}]}],
             'buffers':[{'byteLength':len(data)}],'bufferViews':views,'accessors':accessors}
    for i in range(2,joint_count):
        node=len(model['nodes']);model['nodes'].append({'name':f'FixtureBone{i}','translation':[.07 if i==joint_count-1 else 0,0,0]})
        model['nodes'][0]['children'].append(node);model['skins'][0]['joints'].append(node)
    raw = json.dumps(model,separators=(',',':')).encode()
    raw += b' '*((-len(raw))%4); data.extend(b'\0'*((-len(data))%4))
    glb = struct.pack('<III',0x46546c67,2,28+len(raw)+len(data)) + struct.pack('<I4s',len(raw),b'JSON') + raw + struct.pack('<I4s',len(data),b'BIN\0') + data
    output = Path(output);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(glb)
    print(f'Authored {output}: {len(vertices)} vertices, {len(indices)//3} triangles, {joint_count} bones, three morph targets')


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('--joints',type=int,default=2);a=p.parse_args()
    make_character(a.output,a.joints)
