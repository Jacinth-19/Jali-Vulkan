"""Run with Blender --background --factory-startup --python ... -- <proof dir>."""
import json
from pathlib import Path
import sys
import bpy
root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(root/'imported/character.glb'))
bpy.ops.export_scene.gltf(filepath=str(root/'blender-roundtrip.glb'),export_format='GLB',export_skins=True,export_morph=True,export_yup=True)
(root/'blender-version.json').write_text(json.dumps({'version':bpy.app.version_string,'factory_startup':True,'embedded_python':sys.version,'input':'Synthetic 3-bone / 13-morph fixture; not arbitrary character approval'},indent=2))
