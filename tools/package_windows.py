#!/usr/bin/env python3
"""Build an opt-in portable Windows CPU/WebGL app from explicitly prepared assets.

Does not include recordings, credentials, caches other than the pinned analyzer,
unless explicitly requested, the native Vulkan executable. Never bundles a GPU driver.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def studio_assets(source, relative):
    """Only prepared static assets, never arbitrary session/workspace files."""
    source=Path(source).resolve();relative=Path(relative)
    names=['av-probe.html','index.html','style.css','viewer.js','controller.js','demo-data.js','rig.json','native-shapes.json','character.json','appearance-assets.json','model/mpfb-head.glb','model/low.glb','model/low.glb.json']
    files=[source/name for name in names if (source/name).is_file()]
    if (source/'licenses').exists():files.extend(f for f in (source/'licenses').rglob('*') if f.is_file())
    assets=[]
    for f in files:
        if f.is_symlink() or not f.resolve().is_relative_to(source):raise ValueError('Prepared asset symlink/path escape')
        assets.append((str(f),str(relative/f.relative_to(source).parent)))
    return assets


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--personal-build',action='store_true',required=True,help='Acknowledge local personal use only; redistribution/source compliance is not established');parser.add_argument('--no-archive',action='store_true',help='CI: test directory without creating a distributable ZIP');parser.add_argument('--include-native',action='store_true',help='Include an already built Windows Vulkan renderer, decoded rig, shaders and loader; no GPU driver');parser.add_argument('--studio',type=Path,default=ROOT/'artifacts/neural-studio',help='Explicit prepared default studio (male or female)');parser.add_argument('--female-studio',type=Path,help='Optional prepared female alongside default male; enables selector, WebGL-only');parser.add_argument('--output',type=Path,default=ROOT/'artifacts/windows-portable');args=parser.parse_args()
    if sys.platform!='win32' or platform.machine().lower() not in ('amd64','x86_64'):raise RuntimeError('Build on Windows x64')
    from local_neural_speech import verify_assets
    from analyze_neural_clips import verify_engine
    from neural_platform import analyzer_path
    verify_assets(ROOT/'models/kokoro');verify_engine(analyzer_path())
    if importlib.metadata.version('pyinstaller')!='6.16.0':raise RuntimeError('Install pyinstaller==6.16.0 explicitly')
    dest=args.output.resolve();studio=args.studio.resolve()
    from character_studio_server import prepared_rig
    rig=prepared_rig(studio)
    if args.female_studio:
        if args.include_native:raise ValueError('Paired selector is explicitly WebGL-only')
        female_rig=prepared_rig(args.female_studio)
        if female_rig['model_sha256']==rig['model_sha256']:raise ValueError('Character pair must have distinct models')
    dest.mkdir(parents=True,exist_ok=True)
    # Positive allowlist: never collect a whole checkout, home directory or cache.
    assets=[]
    for source,relative in [(ROOT/'models/kokoro','models/kokoro'),(analyzer_path().parent,'.cache/lipsync/rhubarb-windows')]:
        for f in source.rglob('*'):
            if f.is_file() and 'proof' not in f.relative_to(source).parts:
                assets.append((str(f),str(Path(relative)/f.relative_to(source).parent)))
    assets.extend(studio_assets(studio,'artifacts/neural-studio'))
    if args.female_studio:assets.extend(studio_assets(args.female_studio,'artifacts/character-female'))
    native_binaries=[]
    if args.include_native:
        if (studio/'appearance-assets.json').is_file():raise ValueError('Authored appearance assets are WebGL-only; use the separate stock native build')
        if rig['profile']!='mpfb-rhubarb-9-v1':raise ValueError('Custom imports require an explicit native port; build WebGL-only')
        for filename in ('jali_rich.exe','vulkan-1.dll'):
            file=ROOT/'build-live'/filename
            if not file.is_file():raise RuntimeError('Run windows/setup-native.ps1 before --include-native')
            native_binaries.append((str(file),'native'))
        native_asset=ROOT/'artifacts/native-head/mpfb-native.glb'
        if not native_asset.is_file():raise RuntimeError('Prepare the native character first')
        assets.append((str(native_asset),'native'))
        for name in ('face.comp.spv','skin.comp.spv','mesh.vert.spv','mesh.frag.spv'):
            file=ROOT/'build-live/shaders'/name
            if not file.is_file():raise RuntimeError(f'Missing native shader: {name}')
            assets.append((str(file),'native/shaders'))
        for directory,filename in [('Vulkan-Loader-1.3.290','LICENSE.txt'),('Vulkan-Headers-1.3.290','LICENSE.md'),('tinygltf-2.9.3','LICENSE')]:
            target=dest/'native-notices'/directory;target.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/'.cache/deps'/directory/filename,target/filename)
            assets.append((str(target/filename),'native/licenses/'+directory))
    spec=dest/'JaliStudio.spec'
    spec.write_text('''from PyInstaller.utils.hooks import collect_all, copy_metadata
import importlib.metadata
datas='''+repr(assets)+'''
binaries='''+repr(native_binaries)+''';hiddenimports=[]
for package in ('kokoro_onnx','onnxruntime','phonemizer','espeakng_loader','segments','language_tags'):
    d,b,h=collect_all(package);datas+=d;binaries+=b;hiddenimports+=h
for distribution in importlib.metadata.distributions():
    name=distribution.metadata.get('Name')
    if name:datas+=copy_metadata(name)
a=Analysis(['''+repr(str(ROOT/'tools/portable_entry.py'))+'''],pathex=['''+repr(str(ROOT/'tools'))+'''],binaries=binaries,datas=datas,hiddenimports=hiddenimports,excludes=['pytest','imageio_ffmpeg','pocketsphinx','scipy'])
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='JaliStudio',console=True)
coll=COLLECT(exe,a.binaries,a.datas,name='JaliStudio')
''',encoding='utf-8')
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--distpath',str(dest/'app'),'--workpath',str(dest/'work'),str(spec)],cwd=ROOT,check=True,timeout=600)
    app=dest/'app/JaliStudio'
    if any('ffmpeg' in p.name.lower() and p.suffix.lower() in ('.exe','.dll') for p in app.rglob('*')):raise RuntimeError('Development-only FFmpeg leaked into personal bundle')
    (app/'PERSONAL-BUILD-ONLY.txt').write_text('Personal local build only. Do not publish this bundle.\nphonemizer-fork is GPL-3.0 and espeakng-loader embeds eSpeak.\nComplete corresponding source, notices and combined-work redistribution\nobligations have NOT been established. Metadata alone is not compliance.\nThis does not change the repository license.\n',encoding='utf-8')
    (app/'START-HERE.txt').write_text('Jali portable CPU neural face studio\n\nExtract the ENTIRE ZIP to a writable folder, then double-click JaliStudio.exe.\nIt opens the local renderer/preset launcher; Launch opens your browser. No Python, Node, GitHub account,\nadmin installation, speech API, or runtime model download is required.\nKeep the launcher open; use Stop studio or close it to stop its server. Windows SmartScreen may warn\nbecause this personal build is unsigned. Do not disable system security.\n\nVoice: stock Kokoro af_heart, not a clone. Human rig: CC0 MPFB/MakeHuman.\nWhole utterance or bounded sentence-batched playback; not incremental Kokoro.\nWebGL is always available; native Vulkan requires an explicitly native-enabled build.\nSessions live under %LOCALAPPDATA%\\JaliVulkan\\sessions and old UUID folders\nare cleared on startup. Save desired WAVs before closing/restarting.\nNo public authentication; service is restricted to 127.0.0.1.\n\nLicense notices are in _internal/models/kokoro/licenses,\n_internal/artifacts/neural-studio/licenses, _internal/.cache/lipsync/rhubarb-windows,\nand the bundled Python package metadata/third-party notices.\nSource: https://github.com/Jacinth-19/Jali-Vulkan\n',encoding='utf-8')
    with (app/'START-HERE.txt').open('a',encoding='utf-8') as f:f.write('\nStartup verifies every bundled file against installation-manifest.json.\nFor a machine-readable offline check (no server or session deletion), run:\n  .\\JaliStudio.exe --verify-installation\n  .\\JaliStudio.exe --verify-installation --diagnostics-file "$env:TEMP\\Jali-install-check.json"\nMissing/modified/unexpected files fail closed. Extract into a new EMPTY folder.\nKeep recordings and notes outside the application folder.\nThis manifest detects damage, not authenticity: it is not a digital signature.\nIf the EXE cannot start at all, retain its console error and rebuild from the\ntrusted source; do not disable SmartScreen or fetch random replacement DLLs.\n')
    if args.include_native:
        (app/'Native-Studio.cmd').write_text('@echo off\n"%~dp0JaliStudio.exe" --native %*\n',encoding='utf-8')
        with (app/'START-HERE.txt').open('a',encoding='utf-8') as f:f.write('\nOptional native Vulkan is included. Start Native-Studio.cmd, then select\nNative Vulkan in Face renderer. Uses your installed system GPU driver;\nno GPU driver/Chrome DLL is bundled. Use ordinary EXE launch for WebGL.\nNative shader paths are relocatable; logs stay under LOCALAPPDATA.\n')
    receipt={'schema':'jali-windows-portable-v1','personal_build_only':True,'redistribution_compliance_reviewed':False,'voice':'stock per-character Kokoro voices' if args.female_studio else 'stock af_heart','renderer':'WebGL + optional native Vulkan' if args.include_native else 'WebGL','native_included':args.include_native,'character_selector':bool(args.female_studio),'default_model_sha256':rig['model_sha256'],'default_rig':rig,'gpu_driver_bundled':False,'runtime_downloads':False,'signed':False,'development_modules_excluded':['pytest','imageio_ffmpeg','pocketsphinx','scipy'],
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'build_packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions() if d.metadata.get('Name')},
        'limits':'Portable personal build, not a signed consumer installer or target-laptop/hardware/perceptual acceptance.'}
    (app/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (dest/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if args.female_studio:
        with (app/'START-HERE.txt').open('a',encoding='utf-8') as f:f.write('\nPrepared male/female selector enabled. Default mesh is male (am_michael when prepared). Switching unloads the\nold renderer, then navigates to a fresh document. One renderer per origin/browser profile; other tabs wait before model fetch/decode.\nDifferent origins, profiles and browser apps remain separate. Both rigs share one CPU job.\nNative renderer is not included in this paired WebGL build.\n')
    from package_integrity import create_manifest,verify_installation
    create_manifest(app)
    check=verify_installation(app)
    if not check['verified']:raise RuntimeError(f'New package failed integrity verification: {check}')
    (dest/'integrity-build-check.json').write_text(json.dumps(check,indent=2)+'\n')
    if args.no_archive:print(app);return
    archive=shutil.make_archive(str(dest/'JaliStudio-Windows-x64'),'zip',root_dir=dest/'app',base_dir='JaliStudio')
    from package_integrity import digest
    Path(archive+'.sha256').write_text(digest(Path(archive))+'  '+Path(archive).name+'\n')
    print(archive)


if __name__=='__main__':main()
